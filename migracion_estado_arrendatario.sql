ALTER TABLE inmueble ADD COLUMN estado VARCHAR(20) DEFAULT 'disponible';
ALTER TABLE inmueble ADD COLUMN arrendatario_nombre VARCHAR(120);
ALTER TABLE inmueble ADD COLUMN arrendatario_tipo_doc VARCHAR(30);
ALTER TABLE inmueble ADD COLUMN arrendatario_num_doc VARCHAR(50);
ALTER TABLE inmueble ADD COLUMN arrendatario_telefono VARCHAR(50);
ALTER TABLE inmueble ADD COLUMN arrendatario_correo VARCHAR(120);
ALTER TABLE inmueble ADD COLUMN arrendatario_fecha_pago DATE;
ALTER TABLE inmueble ADD COLUMN arrendatario_descripcion TEXT;