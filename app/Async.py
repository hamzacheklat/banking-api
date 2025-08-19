async with CyberArkConnection(env="stg") as conn:
    resp = await conn.get("api/v1/test")
    print(resp.text)
