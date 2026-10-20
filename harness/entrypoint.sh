#!/bin/sh
php /harness/db-init.php || exit 1
exec php -S 0.0.0.0:8080 -t /harness /harness/app.php
