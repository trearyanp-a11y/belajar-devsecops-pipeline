"use strict";

const toggle = document.getElementById("togglePassword");
const password = document.getElementById("password");
toggle.addEventListener("click", () => {
    const visible = password.type === "password";
    password.type = visible ? "text" : "password";
    toggle.textContent = visible ? "Sembunyikan" : "Lihat";
    toggle.setAttribute("aria-pressed", String(visible));
    toggle.setAttribute("aria-label", visible ? "Sembunyikan password" : "Tampilkan password");
});
document.querySelector(".login-form").addEventListener("submit", (event) => {
    const button = event.currentTarget.querySelector('[type="submit"]');
    button.disabled = true;
    button.querySelector("span").textContent = "Memeriksa akun…";
});
window.addEventListener("pageshow", () => {
    const button = document.querySelector('.login-form [type="submit"]');
    button.disabled = false;
    button.querySelector("span").textContent = "Masuk & main";
});
