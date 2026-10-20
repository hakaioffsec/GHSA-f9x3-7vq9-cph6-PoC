FROM php:8.4-cli
RUN apt-get update && apt-get install -y --no-install-recommends unzip && rm -rf /var/lib/apt/lists/* \
    && docker-php-ext-install pdo_mysql
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
ENV COMPOSER_ALLOW_SUPERUSER=1
ARG FRAMEWORK_REF
WORKDIR /srv
RUN composer require --no-interaction --no-progress --no-scripts "laravel/framework:${FRAMEWORK_REF}"
COPY harness /harness
EXPOSE 8080
ENTRYPOINT ["sh", "/harness/entrypoint.sh"]
