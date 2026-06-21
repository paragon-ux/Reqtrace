function rotateRefreshToken(session) {
  // @reqtrace AUTH-SESSION-ROTATION
  const nextToken = `${session.subject}:${session.version + 1}`;

  return {
    subject: session.subject,
    version: session.version + 1,
    refreshToken: nextToken,
    previousRefreshToken: session.refreshToken,
  };
}

module.exports = {
  rotateRefreshToken,
};
