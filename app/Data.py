import os

class CyberArkConnection:
    def __init__(self, env: str = "stg"):
        self.cyberark_cert = write_temp_file(self.config['cyberark_cert'], suffix=".cert")
        self.cyberark_key = write_temp_file(self.config['cyberark_key'], suffix=".key")
        # ...

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        # Nettoyage manuel
        for f in [self.cyberark_cert, self.cyberark_key]:
            try:
                os.remove(f)
            except FileNotFoundError:
                pass
