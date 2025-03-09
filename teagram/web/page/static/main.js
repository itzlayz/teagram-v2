$(document).ready(function() {
  var translations = {
    en: {
      "welcome_message": "Welcome to Teagram-v2. To start, press button below and follow instructions.",
      "welcome_button": "Get Started",
      "enter_tokens_title": "Enter API Tokens",
      "token_instruction1": "Visit the website <a href='https://my.telegram.org' target='_blank'>my.telegram.org</a>",
      "token_instruction2": "Go to 'API development tools'",
      "token_instruction3": "Copy your API ID and API HASH, and enter them in the fields above",
      "api_id_placeholder": "API ID",
      "api_hash_placeholder": "API HASH",
      "submit_tokens": "Submit Tokens",
      "qr_title": "Log in to Telegram by QR Code",
      "instruction1": "Open Telegram on your phone",
      "instruction2": "Go to Settings > Devices > Link Desktop Device",
      "instruction3": "Point your phone at this screen to confirm login",
      "login_by_phone": "LOG IN BY PHONE NUMBER",
      "lang_switch": "Switch to Russian",
      "phone_login_title": "Log in by Phone",
      "phone_number_placeholder": "Phone number",
      "submit_phone": "Submit Phone",
      "phone_code_placeholder": "Confirmation code",
      "submit_code": "Submit Code",
      "back_to_qr": "Back to QR Code",
      "two_factor_title": "Two-Factor Authentication",
      "password_placeholder": "Password",
      "submit_password": "Submit Password",
      "final_message": "Finished! Return to Telegram and wait for inline bot."
    },
    ru: {
      "welcome_message": "Добро пожаловать в Teagram-v2. Чтобы начать, нажмите кнопку ниже и следуйте инструкциям.",
      "welcome_button": "Начать",
      "enter_tokens_title": "Введите API токены",
      "token_instruction1": "Зайдите на сайт <a href='https://my.telegram.org' target='_blank'>my.telegram.org</a>",
      "token_instruction2": "Перейдите в раздел «API development tools»",
      "token_instruction3": "Скопируйте API ID и API HASH, и введите их в поля выше",
      "api_id_placeholder": "API ID",
      "api_hash_placeholder": "API HASH",
      "submit_tokens": "Подтвердить",
      "qr_title": "Войти в Telegram с помощью QR-кода",
      "instruction1": "Откройте Telegram на своем телефоне",
      "instruction2": "Перейдите в Настройки > Устройства > Привязать устройство",
      "instruction3": "Наведите камеру телефона на этот экран для подтверждения входа",
      "login_by_phone": "ВОЙТИ ПО НОМЕРУ ТЕЛЕФОНА",
      "lang_switch": "Switch to English",
      "phone_login_title": "Войти по телефону",
      "phone_number_placeholder": "Номер телефона",
      "submit_phone": "Отправить номер",
      "phone_code_placeholder": "Код подтверждения",
      "submit_code": "Подтвердить код",
      "back_to_qr": "Вернуться к QR-коду",
      "two_factor_title": "Двухфакторная аутентификация",
      "password_placeholder": "Пароль",
      "submit_password": "Подтвердить",
      "final_message": "Готово! Вернитесь в Telegram и ждите inline-бота."
    }
  };

  var currentLanguage = "en";
  var phoneAuthActive = false;

  var isMobile = /Mobi|Android/i.test(navigator.userAgent);
  
  var firstTranslation = false;
  var hasStarted = false;
  
  var enterTokensMessage = null;

  function translatePage(animated) {
    animated = typeof animated !== 'undefined' ? animated : true;
    $('[data-key]').each(function() {
      var key = $(this).data('key');
      if (translations[currentLanguage][key]) {
        if (firstTranslation || !animated) {
          $(this).html(translations[currentLanguage][key]);
        } else {
          $(this).fadeOut(200, function() {
            $(this).html(translations[currentLanguage][key]).fadeIn(200);
          });
        }
      }
    });
    
    $('[data-placeholder-key]').each(function() {
      var key = $(this).data('placeholder-key');
      if (translations[currentLanguage][key]) {
        $(this).attr('placeholder', translations[currentLanguage][key]);
      }
    });
    
    $('[data-button-key]').each(function() {
      var key = $(this).data('button-key');
      if (translations[currentLanguage][key]) {
        if (firstTranslation || !animated) {
          $(this).html(translations[currentLanguage][key]);
        } else {
          $(this).fadeOut(200, function() {
            $(this).html(translations[currentLanguage][key]).fadeIn(200);
          });
        }
      }
    });
    firstTranslation = false;
  }

  translatePage(false);

  if (isMobile) {
    phoneAuthActive = true;
    showWindow("phone-section");
  }

  $("#welcome-btn").click(function() {
    hasStarted = true;
    $("#welcome-section").fadeOut(500, function() {
      if (enterTokensMessage) {
        showWindow("tokens-section");
        enterTokensMessage = null;
      }
    });
  });

  let wsUrl;
  if (window.location.protocol === "https:") {
    wsUrl = "wss://" + window.location.host + "/ws";
  } else {
    wsUrl = "ws://" + window.location.host + "/ws";
  }

  const ws = new WebSocket(wsUrl);

  ws.onopen = function() {
    console.log("WebSocket connected");
  };

  ws.onmessage = function(event) {
    const msg = JSON.parse(event.data);
    const $message = $("#message");

    function updateMessage(text) {
      $message.fadeOut(200, function() {
        $(this).text(text).fadeIn(200);
      });
    }

    switch (msg.type) {
      case "enter_tokens":
        if (hasStarted) {
          showWindow("tokens-section");
          updateMessage("");
        } else {
          enterTokensMessage = true;
        }
        break;

      case "qr_login":
        if (phoneAuthActive) {
          break;
        }

        if (!$("#qr-section").hasClass("active")) {
          showWindow("qr-section");
        }

        $("#qr-container").empty();
        new QRCode(document.getElementById("qr-container"), {
          text: msg.content,
          width: 200,
          height: 200,
          colorDark: "#ffffff",
          colorLight: "#000000",
          correctLevel: QRCode.CorrectLevel.H
        });
        updateMessage("");
        break;

      case "session_password_needed":
        updateMessage(msg.content || "Password required for session.");
        showWindow("password-section");
        break;

      case "message":
        updateMessage(msg.content);
        break;

      case "error":
        updateMessage(msg.content);
        break;

      default:
        console.log("Unknown message type:", msg);
    }
  };

  ws.onclose = function(event) {
    if (event.code === 1000) {
      $("#login-container").fadeOut("slow", function() {
        $("<p>", {
          text: translations[currentLanguage]["final_message"],
          class: "final-message"
        }).appendTo("body").hide().fadeIn("slow");
      });
    }
  };

  function showWindow(windowId) {
    var $currentWindow = $(".window.active");
    if ($currentWindow.length) {
      $currentWindow.fadeOut(300, function() {
        $currentWindow.removeClass("active");
        $("#" + windowId).fadeIn(300, function() {
          $(this).addClass("active");
        });
      });
    } else {
      $("#" + windowId).fadeIn(300, function() {
        $(this).addClass("active");
      });
    }
  }

  $("#tokens-btn").click(function() {
    const api_id = $("#api_id").val();
    const api_hash = $("#api_hash").val();
    ws.send(JSON.stringify({
      type: "tokens",
      API_ID: api_id,
      API_HASH: api_hash
    }));
    showWindow("qr-section");
    $("#message").fadeOut(200, function() {
      $(this).empty().fadeIn(200);
    });
  });

  $("#to-phone").click(function(e) {
    e.preventDefault();
    phoneAuthActive = true;
    showWindow("phone-section");
    $("#message").empty();
  });

  $("#to-qr").click(function(e) {
    e.preventDefault();
    phoneAuthActive = false;
    showWindow("qr-section");
    $("#message").empty();
  });

  $("#phone-number-btn").click(function() {
    const phone_number = $("#phone_number").val();
    ws.send(JSON.stringify({
      type: "phone_number",
      phone_number: phone_number
    }));
    $("#phone-step1").fadeOut("fast", function() {
      $("#phone-step2").fadeIn("fast");
    });
  });

  $("#phone-code-btn").click(function() {
    const phone_code = $("#phone_code").val();
    ws.send(JSON.stringify({
      type: "phone_code",
      phone_code: phone_code
    }));
  });

  $("#password-btn").click(function() {
    const password = $("#login_password").val();
    ws.send(JSON.stringify({
      type: "cloud_auth",
      password: password
    }));
  });

  $("#lang-switch").click(function(e) {
    e.preventDefault();
    currentLanguage = (currentLanguage === "en") ? "ru" : "en";
    translatePage(true);
  });
  
  var greetings = [
    "Hello!", "Привет!", "Hola!", "Bonjour!", "Ciao!", "Hallo!", "Olá!", "Hej!", "Ahoj!", "Szia!",
    "Salam!", "Namaste!", "Konnichiwa!", "Annyeong!", "Merhaba!", "Yassas!", "Shalom!",
    "Salue!", "Sveiki!", "Dobrý den!", "Tere!", "Xin chào!", "Selam!", "Mabuhay!", "Sawadee!",
    "Jambo!", "Habari!", "Bula!", "Kamusta!", "Sawatdee!", "God dag!", "Moien!", "Halo!", "Cześć!"
  ];
  
  function typeEffect(element, text, callback) {
    var index = 0;
    var interval = setInterval(function() {
      $(element).append(text[index]);
      index++;
      if (index === text.length) {
        clearInterval(interval);
        if (callback) setTimeout(callback, 1000);
      }
    }, 100);
  }

  function deleteEffect(element, callback) {
    var text = $(element).text();
    var interval = setInterval(function() {
      text = text.slice(0, -1);
      $(element).text(text);
      if (text.length === 0) {
        clearInterval(interval);
        $(element).html('&nbsp;');
        if (callback) callback();
      }
    }, 50);
  }
  

  function cycleGreetings(greetingsArr, index) {
    var element = document.querySelector('h1[data-key="welcome_title"]');
    if (!element) return;
    typeEffect(element, greetingsArr[index], function() {
      setTimeout(function() {
        deleteEffect(element, function() {
          var nextIndex = (index + 1) % greetingsArr.length;
          cycleGreetings(greetingsArr, nextIndex);
        });
      }, 1000);
    });
  }

  $("#welcome-section").fadeOut(500, function() {
    cycleGreetings(greetings, 0);
    $("#welcome-section").fadeIn(1000);
  });
});
