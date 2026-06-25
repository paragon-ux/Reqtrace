function revokePreviousRefreshToken(store, rotatedSession) {
  // @reqtrace AUTH-SESSION-ROTATION
  // Copy the rotated session and mark the retired token unusable for downstream checks.
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
