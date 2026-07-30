from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+aiomysql://root:@localhost:3306/myokr"
    JWT_SECRET: str = "myokr-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    SSO_PUBLIC_URL: str = "http://localhost:5173"
    SSO_AUTHORIZE_PATH: str = "/authorize"
    SSO_SERVER_URL: str = "http://localhost:8000"
    SSO_CLIENT_ID: str = ""
    SSO_CLIENT_SECRET: str = ""
    SSO_REDIRECT_URI: str = "http://localhost:8001/api/auth/sso/callback"
    FRONTEND_URL: str = "http://localhost:5174"
    SSO_COOKIE_SECURE: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
