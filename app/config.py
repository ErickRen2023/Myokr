from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+aiomysql://root:@localhost:3306/myokr"
    JWT_SECRET: str = "myokr-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
