/**
 * PTA経理 レシート自動記帳システム
 *
 * LINE公式アカウントにレシート写真を送るだけで、Gemini APIが内容を読み取り、
 * Googleスプレッドシートに自動記帳・Googleドライブに原本画像を保存する。
 *
 * 費用: LINE Messaging API の応答メッセージ / GAS / スプレッドシート / ドライブは無料。
 *       Gemini API は無料枠（gemini-2.5-flash, 1日あたり数百リクエスト）内で運用する前提。
 *       PTA規模の利用量であれば課金なしで継続運用できる見込みだが、
 *       各社の無料枠条件は将来変更されうるため定期的に確認すること。
 *
 * 事前準備（スクリプトプロパティ）:
 *   [拡張機能] > [Apps Script] > 左メニューの歯車アイコン[プロジェクトの設定] > [スクリプト プロパティ] に以下を設定する。
 *     LINE_CHANNEL_ACCESS_TOKEN … LINE公式アカウントのチャネルアクセストークン（長期）
 *     GEMINI_API_KEY            … Google AI StudioのGemini APIキー
 *     SHEET_ID                  … 記帳先スプレッドシートのID
 *     DRIVE_FOLDER_ID           … レシート画像保存先ドライブフォルダのID
 *   任意:
 *     GEMINI_MODEL … 既定 "gemini-2.5-flash"
 *     SHEET_NAME   … 既定 "記帳台帳"
 *
 * デプロイ: [デプロイ] > [新しいデプロイ] > 種類「ウェブアプリ」
 *   実行ユーザー: 自分／アクセスできるユーザー: 全員
 *   発行されたURLをLINE Developersコンソールの Webhook URL に設定する。
 *
 * セキュリティ上の注意:
 *   GAS の doPost(e) では HTTP リクエストヘッダーを取得できないため、
 *   LINEが付与する署名(X-Line-Signature)による検証は実装できない。
 *   対策として、Web AppのURLを第三者に開示しないこと、
 *   および記帳結果は人間が最終確認する運用（needs_review フラグ）で担保する。
 */

// PTA向け勘定科目（必要に応じて増減してよい）
var CATEGORIES = [
  '文具費', '印刷製本費', '通信費', '交通費', '会議費',
  '行事費', '消耗品費', '会場費', '保険料', '謝礼', '慶弔費', '雑費'
];

var SHEET_HEADERS = [
  '記帳日時', '日付', '支払先', '金額', '品目', '勘定科目',
  '要確認', '画像URL', 'LINEユーザーID', 'メッセージID'
];

/**
 * 設定値をスクリプトプロパティから取得する。
 */
function getConfig_() {
  var props = PropertiesService.getScriptProperties().getProperties();
  var required = ['LINE_CHANNEL_ACCESS_TOKEN', 'GEMINI_API_KEY', 'SHEET_ID', 'DRIVE_FOLDER_ID'];
  var missing = required.filter(function (key) { return !props[key]; });
  if (missing.length > 0) {
    throw new Error('スクリプトプロパティが未設定です: ' + missing.join(', '));
  }
  return {
    lineChannelAccessToken: props.LINE_CHANNEL_ACCESS_TOKEN,
    geminiApiKey: props.GEMINI_API_KEY,
    geminiModel: props.GEMINI_MODEL || 'gemini-2.5-flash',
    sheetId: props.SHEET_ID,
    sheetName: props.SHEET_NAME || '記帳台帳',
    driveFolderId: props.DRIVE_FOLDER_ID
  };
}

/**
 * LINEからのWebhookエントリポイント。
 */
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput('OK');
    }
    var config = getConfig_();
    var body = JSON.parse(e.postData.contents);
    var events = body.events || [];

    events.forEach(function (event) {
      try {
        handleEvent_(event, config);
      } catch (err) {
        Logger.log('handleEvent_ error: ' + err + '\n' + err.stack);
        if (event.replyToken) {
          try {
            replyText_(event.replyToken, '記帳に失敗しました。恐れ入りますが、もう一度写真を送るか、事務局にご連絡ください。', config);
          } catch (replyErr) {
            Logger.log('replyText_ error: ' + replyErr);
          }
        }
      }
    });

    return ContentService.createTextOutput('OK');
  } catch (err) {
    Logger.log('doPost error: ' + err + '\n' + err.stack);
    return ContentService.createTextOutput('OK'); // LINE側の再送ループを避けるため常に200を返す
  }
}

/**
 * 1件のLINEイベントを処理する。
 */
function handleEvent_(event, config) {
  if (event.type !== 'message' || event.message.type !== 'image') {
    if (event.replyToken) {
      replyText_(event.replyToken, 'レシートの写真を送ってください。自動で読み取って記帳します。', config);
    }
    return;
  }

  var messageId = event.message.id;
  var userId = event.source && event.source.userId ? event.source.userId : '';

  var imageBlob = fetchLineImage_(messageId, config);
  var driveUrl = saveImageToDrive_(imageBlob, messageId, config);
  var data = analyzeReceiptWithGemini_(imageBlob, config);

  appendRow_(data, driveUrl, userId, messageId, config);

  var summary = buildReplyMessage_(data);
  if (event.replyToken) {
    replyText_(event.replyToken, summary, config);
  }
}

/**
 * LINEのContent APIから画像バイナリを取得する。
 */
function fetchLineImage_(messageId, config) {
  var url = 'https://api-data.line.me/v2/bot/message/' + messageId + '/content';
  var response = UrlFetchApp.fetch(url, {
    method: 'get',
    headers: { Authorization: 'Bearer ' + config.lineChannelAccessToken },
    muteHttpExceptions: true
  });
  if (response.getResponseCode() !== 200) {
    throw new Error('LINE画像取得に失敗しました: ' + response.getResponseCode() + ' ' + response.getContentText());
  }
  return response.getBlob();
}

/**
 * 画像をGoogleドライブに保存し、閲覧用URLを返す。
 */
function saveImageToDrive_(imageBlob, messageId, config) {
  var folder = DriveApp.getFolderById(config.driveFolderId);
  var timestamp = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMMdd_HHmmss');
  var filename = 'receipt_' + timestamp + '_' + messageId + '.jpg';
  imageBlob.setName(filename);
  var file = folder.createFile(imageBlob);
  return file.getUrl();
}

/**
 * Gemini APIにレシート画像を送り、記帳に必要な項目をJSONで抽出する。
 */
function analyzeReceiptWithGemini_(imageBlob, config) {
  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
    config.geminiModel + ':generateContent?key=' + config.geminiApiKey;

  var base64Image = Utilities.base64Encode(imageBlob.getBytes());
  var mimeType = imageBlob.getContentType() || 'image/jpeg';

  var prompt = [
    'あなたはPTA(保護者と先生の会)の経理担当を補助するアシスタントです。',
    '添付されたレシート・領収書の画像を読み取り、以下のJSON形式のみで出力してください。',
    '説明文やコードブロックのマークダウンは付けず、JSONオブジェクト1つだけを出力すること。',
    '',
    '{',
    '  "date": "YYYY-MM-DD形式の支払日。読み取れない場合は空文字",',
    '  "vendor": "支払先の店名・会社名。読み取れない場合は空文字",',
    '  "amount": 合計金額を表す数値（円、カンマなし）。読み取れない場合は 0,',
    '  "item": "購入品目・内容の要約（20文字程度）",',
    '  "category": "次の勘定科目のいずれか1つ: ' + CATEGORIES.join('、') + '",',
    '  "needs_review": 読み取りに自信が持てない、またはレシート画像として不鮮明な場合は true、そうでなければ false',
    '}'
  ].join('\n');

  var payload = {
    contents: [{
      parts: [
        { text: prompt },
        { inlineData: { mimeType: mimeType, data: base64Image } }
      ]
    }],
    generationConfig: {
      temperature: 0.1,
      responseMimeType: 'application/json'
    }
  };

  var response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  if (response.getResponseCode() !== 200) {
    throw new Error('Gemini API呼び出しに失敗しました: ' + response.getResponseCode() + ' ' + response.getContentText());
  }

  var result = JSON.parse(response.getContentText());
  var text = result.candidates && result.candidates[0] && result.candidates[0].content &&
    result.candidates[0].content.parts && result.candidates[0].content.parts[0].text;
  if (!text) {
    throw new Error('Geminiの応答からテキストを取得できませんでした: ' + response.getContentText());
  }

  var parsed;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new Error('Geminiの応答をJSONとして解釈できませんでした: ' + text);
  }

  return {
    date: parsed.date || '',
    vendor: parsed.vendor || '',
    amount: Number(parsed.amount) || 0,
    item: parsed.item || '',
    category: CATEGORIES.indexOf(parsed.category) !== -1 ? parsed.category : '雑費',
    needsReview: parsed.needs_review === true || !parsed.date || !parsed.amount
  };
}

/**
 * スプレッドシートに1行追加する。
 */
function appendRow_(data, driveUrl, userId, messageId, config) {
  var sheet = getOrCreateSheet_(config);
  sheet.appendRow([
    new Date(),
    data.date,
    data.vendor,
    data.amount,
    data.item,
    data.category,
    data.needsReview ? '要確認' : '',
    driveUrl,
    userId,
    messageId
  ]);
}

/**
 * LINEへテキストメッセージを返信する。
 */
function replyText_(replyToken, text, config) {
  var url = 'https://api.line.me/v2/bot/message/reply';
  var payload = {
    replyToken: replyToken,
    messages: [{ type: 'text', text: text }]
  };
  var response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + config.lineChannelAccessToken },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  if (response.getResponseCode() !== 200) {
    Logger.log('LINE返信に失敗しました: ' + response.getResponseCode() + ' ' + response.getContentText());
  }
}

/**
 * 記帳結果のLINE返信文を組み立てる。
 */
function buildReplyMessage_(data) {
  var lines = ['記帳しました！'];
  lines.push('日付: ' + (data.date || '(不明)'));
  lines.push('支払先: ' + (data.vendor || '(不明)'));
  lines.push('金額: ' + (data.amount ? data.amount.toLocaleString() + '円' : '(不明)'));
  lines.push('勘定科目: ' + data.category);
  if (data.item) {
    lines.push('品目: ' + data.item);
  }
  if (data.needsReview) {
    lines.push('');
    lines.push('※ 読み取り内容に自信が持てない項目があります。スプレッドシートをご確認ください。');
  }
  return lines.join('\n');
}

/**
 * 記帳先シートを取得する。存在しなければヘッダー付きで新規作成する。
 */
function getOrCreateSheet_(config) {
  var ss = SpreadsheetApp.openById(config.sheetId);
  var sheet = ss.getSheetByName(config.sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(config.sheetName);
    sheet.appendRow(SHEET_HEADERS);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

/**
 * 【手動実行用】シートの初期セットアップ（ヘッダー作成）。
 * Apps Scriptエディタでこの関数を選んで実行する。
 */
function setupSheet() {
  var config = getConfig_();
  var sheet = getOrCreateSheet_(config);
  Logger.log('シート "' + sheet.getName() + '" の準備ができました。');
}

/**
 * 【手動実行用】設定値と外部接続の疎通確認。
 * Apps Scriptエディタでこの関数を選んで実行する。
 */
function checkSettings() {
  var config = getConfig_();
  Logger.log('スクリプトプロパティ: OK');

  var ss = SpreadsheetApp.openById(config.sheetId);
  Logger.log('スプレッドシート接続: OK (' + ss.getName() + ')');

  var folder = DriveApp.getFolderById(config.driveFolderId);
  Logger.log('ドライブフォルダ接続: OK (' + folder.getName() + ')');

  var lineCheck = UrlFetchApp.fetch('https://api.line.me/v2/bot/info', {
    method: 'get',
    headers: { Authorization: 'Bearer ' + config.lineChannelAccessToken },
    muteHttpExceptions: true
  });
  Logger.log('LINEチャネル接続: ' + (lineCheck.getResponseCode() === 200 ? 'OK' : 'NG (' + lineCheck.getResponseCode() + ')'));

  Logger.log('すべての確認が完了しました。問題がなければ setupSheet() を実行し、Webアプリとしてデプロイしてください。');
}
