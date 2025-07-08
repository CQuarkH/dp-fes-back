# Sistema de Gestión de Documentos con Firma Digital - Backend
Proyecto desarrollado para la asignatura de Dirección de Proyectos.

Integrantes: 
- Benjamin San Martin
- Vicente Marquez
- Cristóbal Pavez
- Carlos Moris
- Sebastián Ávila
- Elías Currihuil

## Plan de Pruebas
La implementación del Plan de Pruebas está disponible dentro de la carpeta `tests`. Ahí también se encuentra un reporte a modo de registro de ejecución de las pruebas, en formato PDF y HTML (con el nombre `reporte_pruebas`).

### Ejecución de las Pruebas

Para ejecutar las pruebas, es necesario clonar el repositorio.

Una vez que se tiene el repositorio clonado y dentro de la raíz del proyecto, se deben instalar las dependencias con:
```
pip install -r requirements.txt
```

Luego, se debe levantar el contenedor Docker con el siguiente comando: 
```
docker-compose up --build
```

Finalmente, con el contenedor Docker corriendo, las pruebas se ejecutan con el siguiente comando: 
```
pytest
```
