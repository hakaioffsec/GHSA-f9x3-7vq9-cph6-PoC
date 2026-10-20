<?php

require '/srv/vendor/autoload.php';

use Illuminate\Database\Capsule\Manager as Capsule;

$capsule = new Capsule;
$capsule->addConnection([
    'driver' => 'mysql',
    'host' => getenv('DB_HOST') ?: 'mysql',
    'database' => 'forge',
    'username' => 'root',
    'password' => '',
]);
$capsule->setAsGlobal();

for ($i = 0; ; $i++) {
    try {
        Capsule::schema()->hasTable('users');
        break;
    } catch (Throwable $e) {
        if ($i > 60) {
            throw $e;
        }
        sleep(1);
    }
}

if (! Capsule::schema()->hasTable('users')) {
    try {
        Capsule::schema()->create('users', function ($table) {
            $table->id();
            $table->string('email');
            $table->string('api_token');
        });
    } catch (Throwable $e) {
    }
}

Capsule::table('users')->insertOrIgnore([
    ['id' => 1, 'email' => 'user@email.com', 'api_token' => 'b7f9d2c4a8e6b1f3d5a0c9e2b4d6f8a1c'],
    ['id' => 2, 'email' => 'user2@email.com', 'api_token' => '2d4f6h8j1l3n5p7r9t1v3x5z7b9d1f3'],
]);

echo "db ready: users seeded\n";
