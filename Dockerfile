FROM php:8.2-cli

# Kerakli tizim papkalarini oldindan yaratamiz va ruxsat beramiz
RUN mkdir -p /app/step /app/komm && chmod -R 777 /app

# Loyihaning barcha fayllarini nusxalaymiz
COPY . /app
WORKDIR /app

# Render bergan dinamik portni ishga tushirish qismiga biriktiramiz
CMD ["sh", "-c", "php -S 0.0.0.0:8080 bot.php"]

