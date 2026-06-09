const assert = require("node:assert/strict");

const { rotateRefreshToken } = require("../src/rotation");
const { revokePreviousRefreshToken, isRefreshTokenRevoked } = require("../src/revocation");
const { validateRefreshRequest } = require("../src/validation");

function testRefreshTokenRotationPreventsReuse() {
  // @reqtrace AUTH-SESSION-ROTATION/004/@file
  const request = validateRefreshRequest({
    refreshToken: "alice:1",
    subject: "alice",
  });

  const session = {
    subject: request.subject,
    version: 1,
    refreshToken: request.refreshToken,
  };
  const rotatedSession = rotateRefreshToken(session);
  const store = { revokedTokens: new Set() };

  revokePreviousRefreshToken(store, rotatedSession);

  assert.equal(rotatedSession.refreshToken, "alice:2");
  assert.equal(isRefreshTokenRevoked(store, "alice:1"), true);
  assert.equal(isRefreshTokenRevoked(store, "alice:2"), false);
}

testRefreshTokenRotationPreventsReuse();
