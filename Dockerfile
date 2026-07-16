FROM php:8.2-cli

# Kerakli tizim papkalarini oldindan yaratamiz va ruxsat beramiz
RUN mkdir -p /app/step /app/kino && chmod -R 777 /app

COPY . /app
WORKDIR /app

# Serverni har doim ishlab turishi uchun PHP built-in serverini yoqamiz
CMD [ "php", "-S", "0.0.0.0:10000", "bot.php" ]
