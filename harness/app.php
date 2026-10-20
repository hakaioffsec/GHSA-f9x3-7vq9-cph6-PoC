<?php

require '/srv/vendor/autoload.php';

use Illuminate\Auth\EloquentUserProvider;
use Illuminate\Auth\TokenGuard;
use Illuminate\Database\Capsule\Manager as Capsule;
use Illuminate\Hashing\BcryptHasher;
use Illuminate\Http\Request;

class PocUser extends Illuminate\Database\Eloquent\Model
{
    protected $table = 'users';
    public $timestamps = false;
}

$capsule = new Capsule;
$capsule->addConnection([
    'driver' => 'mysql',
    'host' => getenv('DB_HOST') ?: 'mysql',
    'database' => 'forge',
    'username' => 'root',
    'password' => '',
]);
$capsule->setAsGlobal();
$capsule->bootEloquent();

header('Content-Type: application/json');

$request = Request::capture();
$started = microtime(true);

$guard = new TokenGuard(new EloquentUserProvider(new BcryptHasher, 'PocUser'), $request);
$user = $guard->user();
$elapsed = round((microtime(true) - $started) * 1000);

if ($user) {
    http_response_code(200);
    echo json_encode(['authenticated_as' => $user->email, 'user_id' => $user->id]);
} else {
    http_response_code(401);
    echo json_encode(['error' => 'unauthenticated']);
}

file_put_contents(
    getenv('LOG_FILE') ?: 'php://stderr',
    sprintf(
        "[%s] %s %s api_token=%s verdict=%d %s %dms\n",
        date('Y-m-d H:i:s'),
        $request->method(),
        $request->path(),
        json_encode($request->input('api_token')),
        http_response_code(),
        $user->email ?? '-',
        $elapsed
    ),
    FILE_APPEND
);
