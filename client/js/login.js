const loginButton = document.querySelector('.login-button');
const logoutButton = document.querySelector('.logout-button');
const loginPopup = document.querySelector('.login-popup');
const usernameInput = document.querySelector('.login-username');
const cancelButton = document.querySelector('.login-cancel-button');
const verifyButton = document.querySelector('.login-verify-button');
const nextButton = document.querySelector('.login-next-button');
const authField = document.querySelector('.login-auth_field');
const authCode = document.querySelector('.login-auth_code');
const errorField = document.querySelector('.login-error');

const loggedInContainer = document.querySelector(".loggedin-container");
const loggedOutContainer = document.querySelector(".loggedout-container");

const userAvatar = document.querySelector(".user-avatar");
const username = document.querySelector(".username");

var userInfos = {};

fetch("/services/authenticate", {
    method: 'POST',
})
.then(response => {
    if (!response.ok) {
        return;
    }
    loggedInContainer.style.display = 'block';
    loggedOutContainer.style.display = 'none';
    response.json()
    .then(data => {
        userInfos = data;
        let avatar_id = userInfos.avatar_id;
        // TODO: Add default image
        userAvatar.src = avatar_id ? `https://static.codingame.com/servlet/fileservlet?id=${avatar_id}&format=navigation_avatar` : "";
        username.textContent = userInfos.username;
    });
})


logoutButton.addEventListener('click', () => {
    fetch("/services/logout", {
        method: 'POST'
    })
    .then(response => {
        location.reload();
    })
});

loginButton.addEventListener('click', () => {
    loginPopup.style.display = 'block';
});

cancelButton.addEventListener('click', () => {
    errorField.textContent = "";
    if (verifyButton.style.display === 'none') {
        loginPopup.style.display = 'none';
        return;
    }
    verifyButton.style.display = 'none';
    authField.style.display = 'none';
    nextButton.style.display = 'inline';
    usernameInput.style.display = 'inline';
});

nextButton.addEventListener('click', () => {
    errorField.textContent = "";
    fetch("/services/login_request", {
        method: 'POST',
        body: JSON.stringify({
            "username": usernameInput.value
        })
    })
    .then(response => {
        response.json()
        .then(data => {
            if (response.ok) {
                nextButton.style.display = 'none';
                usernameInput.style.display = 'none';
                verifyButton.style.display = 'inline';
                authField.style.display = 'block';
                authCode.textContent = data.auth_code;
                return;
            }
            errorField.textContent = data.message;
        });
    });
});

verifyButton.addEventListener('click', () => {
    errorField.textContent = "";
    fetch("/services/login", {
        method: 'POST'
    })
    .then(response => {
        if (response.ok) {
            location.reload();
            return;
        }
        response.json()
        .then(data => {
            errorField.textContent = data.message;
        });
    });
});