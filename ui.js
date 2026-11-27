'use strict';
const themeButton=document.getElementById('theme');
function applyTheme(dark){document.body.classList.toggle('dark',dark);themeButton.setAttribute('aria-pressed',String(dark));themeButton.textContent=dark?'Light':'Dark';}
try{applyTheme(localStorage.getItem('kurdway-theme')==='dark');}catch(e){}
themeButton.addEventListener('click',()=>{const dark=!document.body.classList.contains('dark');applyTheme(dark);try{localStorage.setItem('kurdway-theme',dark?'dark':'light');}catch(e){}});
