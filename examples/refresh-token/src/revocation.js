function revokePreviousRefreshToken(store, rotatedSession) {
  // @reqtrace AUTH-SESSION-ROTATION/003/@file
  store.revokedTokens.add(rotatedSession.previousRefreshToken);

  return {
    ...rotatedSession,
    oldTokenReusable: false,
  };
}

function isRefreshTokenRevoked(store, token) {
  return store.revokedTokens.has(token);
}

module.exports = {
  isRefreshTokenRevoked,
  revokePreviousRefreshToken,
};
