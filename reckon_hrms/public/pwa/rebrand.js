/* Reckon HRMS on the Frappe HR mobile app: the words and the logo the app draws itself.
   The page title, install name, icons and manifest are set on the server (reckon_hrms.pwa). */
(function () {
  var FROM = /Frappe HR/g, TO = "Reckon HRMS", ICON = "/assets/reckon_hrms/pwa/icon-192.png";
  function words(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), node, list = [];
    while ((node = walker.nextNode())) if (FROM.test(node.nodeValue)) list.push(node);
    FROM.lastIndex = 0;
    list.forEach(function (n) { n.nodeValue = n.nodeValue.replace(FROM, TO); });
  }
  function logo(root) {
    // The sign-in screen draws the product mark as an inline image beside "Login to ...".
    root.querySelectorAll("div").forEach(function (box) {
      if (box.children.length === 2 && box.children[1].textContent.indexOf(TO) > -1 && box.children[0].tagName.toLowerCase() === "svg") {
        var img = document.createElement("img");
        img.src = ICON; img.alt = TO; img.className = "h-8 w-8 rounded-lg"; img.style.cssText = "width:32px;height:32px;border-radius:8px";
        box.replaceChild(img, box.children[0]);
      }
    });
  }
  function run() {
    var app = document.getElementById("app");
    if (!app) return;
    try { words(app); logo(app); document.title = document.title.replace(FROM, TO); } catch (e) { /* the app still works unbranded */ }
  }
  var pending = false;
  new MutationObserver(function () {
    if (pending) return; pending = true;
    requestAnimationFrame(function () { pending = false; run(); });
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  document.addEventListener("DOMContentLoaded", run);
})();
