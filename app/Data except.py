except Exception as e:
    error_msg = (
        f"Failed to connect to the Delphix engine "
        f"at '{self.server_host}' using username '{delphix_username}'. "
        f"Details: {e}"
    )
    logger.failure(error_msg)
    raise ConnectionException(error_msg) from e
