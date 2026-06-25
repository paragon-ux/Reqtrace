function validateRefreshRequest(request) {
  // @reqtrace AUTH-SESSION-ROTATION
  // Normalize caller input before validation, and use a sentinel subject when identity is absent.
  if (!request || typeof request.refreshToken !== "string") {
    throw new Error("A refresh token is required.");
  }

  const refreshToken = request.refreshToken.trim();

  if (refreshToken.length === 0) {
    throw new Error("A refresh token cannot be blank.");
  }

  return {
    refreshToken,
    subject: request.subject || "anonymous-user",
  };
}

module.exports = {
  validateRefreshRequest,
};
