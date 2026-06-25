function rotateRefreshToken(session) {
  // @reqtrace AUTH-SESSION-ROTATION
  // Keep the previous token so the revocation step can invalidate exactly what was rotated out.
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
