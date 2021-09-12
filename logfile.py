import logging
from logging.handlers import SMTPHandler


LOG_FORMAT = "%(levelname)s:%(asctime)s - %(processName)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("log.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

error_handler = logging.FileHandler("error.log", encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)
logger.addHandler(error_handler)

# smtp_handler = SMTPHandler(
#     mailhost=("smtp.qq.com", 25),
#     fromaddr="1624497311@qq.com",
#     toaddrs=["1624497311@qq.com"],
#     credentials=("1624497311@qq.com", "fvxajcmgbgixfbei"),
#     subject="[自动报警][博客园爬虫]",
# )
# smtp_handler.setLevel(logging.ERROR)
# smtp_handler.setFormatter(formatter)
# logger.addHandler(smtp_handler)
