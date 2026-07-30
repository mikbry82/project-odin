const parameters = new URLSearchParams(window.location.search);
const message = parameters.get("message");
const detail = parameters.get("detail");

if (message) document.querySelector("#message").textContent = message;
if (detail) document.querySelector("#detail").textContent = detail;
