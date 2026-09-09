# Start PostgreSQL using pg_ctl
$pg_ctl = "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
$data_dir = "C:\Program Files\PostgreSQL\18\data"

Write-Host "Starting PostgreSQL with pg_ctl..."
& $pg_ctl start -D $data_dir
Write-Host "Exit code: $?"