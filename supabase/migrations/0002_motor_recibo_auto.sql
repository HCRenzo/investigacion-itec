-- El motor del recibo ahora se elige desde el panel /admin (v1, v2 o auto).
-- 'auto' = cada despliegue usa su variable de entorno RECEIPT_ENGINE. Ejecutar una vez en el SQL Editor.
update t_parametro
   set valor = 'auto',
       descripcion = 'Motor de calculo del recibo: v1 (lento), v2 (rapido) o auto (usa el entorno)'
 where clave = 'MOTOR_RECIBO' and deleted_at is null;
