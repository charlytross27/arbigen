# Arbigen

**Investiga productos antes de venderlos y crea imágenes para presentarlos mejor.**

Arbigen reúne información de publicaciones de Mercado Libre, el interés de búsqueda de Google Trends y los costos que tú conoces. Con esos datos puedes comparar precios, explorar productos similares y probar si una venta tendría margen. Cuando eliges un producto, Estudio IA te ayuda a crear imágenes a partir de una fotografía original.

La aplicación está pensada para revendedores independientes, emprendedores y pequeños comercios. **Sus resultados sirven para investigar; no garantizan ventas ni sustituyen tu decisión comercial.**

[Abrir Arbigen](https://arbigen-web.vercel.app/)

> El registro es privado. Para crear una cuenta necesitas un código de invitación del administrador. Tus investigaciones y catálogos se muestran únicamente en tu cuenta.

## Qué puedes hacer

- **Investigar un producto.** Guarda una palabra clave y elige México, Colombia o Argentina.
- **Examinar una muestra del mercado.** Consulta publicaciones relacionadas, revisa sus precios y conoce cuántos datos pudieron aprovecharse.
- **Seguir el interés de búsqueda.** Importa un CSV de Google Trends para visualizar la evolución del término y, si hay datos suficientes, un pronóstico orientativo del índice.
- **Evaluar tus números.** Introduce tu precio de venta y tus costos para calcular utilidad, margen y retorno por unidad. Puedes probar otros supuestos sin cambiar el escenario guardado.
- **Crear un catálogo visual.** Sube una foto, genera imágenes con Estudio IA, selecciona las que te sirvan y guárdalas en tu cuenta.

## Tu primer análisis

1. Entra con tu cuenta y abre **Explorar oportunidades**. Escribe el producto que quieres investigar y selecciona el país. Al guardar la búsqueda se crea una ficha en **Mis análisis**; todavía no se consulta el mercado.
2. En la ficha, pulsa **Consultar y preparar** para obtener una muestra de publicaciones. Arbigen mostrará los precios disponibles y el resultado de la preparación de datos. Si ya tienes una muestra, **Actualizar datos guardados sin nueva búsqueda** vuelve a procesarla sin consultar al proveedor.
3. Si quieres analizar el interés a lo largo del tiempo, exporta desde [Google Trends](https://trends.google.com/trends/) el CSV de **«Interés a lo largo del tiempo»** para la misma palabra clave y el mismo país. Vuelve a la ficha y usa **Importar CSV**.
4. Revisa la distribución de precios, los grupos de productos y la tendencia. Si faltan datos suficientes, Arbigen lo indicará en lugar de mostrar una cifra inventada.
5. Abre **Evaluar rentabilidad**, elige una publicación como referencia e introduce **tu propio** precio de venta, costo del producto, envío, comisión y otros gastos. Pulsa **Guardar escenario** si quieres conservar esos valores.
6. Si deseas preparar imágenes, entra en **Estudio IA** desde el producto elegido o desde el menú. Sube una fotografía, define el estilo y la escena, revisa el resultado y pulsa **Crear catálogo** para guardar las vistas seleccionadas.

Puedes dejar una investigación a medias y retomarla desde **Mis análisis**. Abrir una ficha guardada no inicia por sí solo una nueva consulta de productos.

## Cómo interpretar los resultados

| Resultado | Qué te dice | Qué no debes concluir |
| --- | --- | --- |
| Precios y grupos | Cómo se distribuyen y se parecen las publicaciones de la muestra guardada. | Que toda la categoría tenga esos precios o que un grupo venda más. |
| Google Trends y pronóstico | Cómo ha variado el interés relativo por el término y qué patrón podría continuar a corto plazo. | Cuántas búsquedas o ventas habrá. |
| Utilidad, margen y retorno | Qué ocurriría por unidad con el precio y los costos que introdujiste. | Que esos costos o la cantidad de ventas estén verificados. |
| Puntuación exploratoria | Combina interés, desempeño histórico del pronóstico y rentabilidad. | Una probabilidad de éxito o una recomendación automática de compra. |

La muestra puede contener publicaciones sin precio o señales no informadas. Arbigen indica las exclusiones y las advertencias de calidad. Un valor ausente no significa cero. El precio observado de otro vendedor tampoco es tu costo de adquisición.

## Consultas y generación de imágenes

**Consultar y preparar** y **Actualizar y preparar** inician una nueva búsqueda de productos. **Generar imágenes**, regenerar o añadir una variación inicia una solicitud al servicio de imágenes. Estas acciones pueden generar un costo para quien administra Arbigen.

Volver a abrir una investigación, reprocesar la muestra guardada, calcular otro escenario, comprobar el resultado de una generación en curso y descargar datos para el cuaderno **no** inician esas consultas pagadas.

Estudio IA acepta fotografías PNG, JPEG o WebP de hasta 10 MB. Revisa las imágenes generadas antes de publicarlas: los detalles del producto pueden diferir de la fotografía original.

## Analizar tus datos en un cuaderno

En la ficha de una investigación, pulsa **Descargar datos para el cuaderno**. Puedes subir ese JSON a Google Colab y abrir el [cuaderno de ciencia de datos](notebooks/arbigen_ciencia_de_datos.ipynb) para recorrer la limpieza, la exploración, los grupos y el pronóstico. No necesitas volver a consultar Apify ni conectar Colab a la base de datos.

Si también quieres estudiar tus costos en el cuaderno, pulsa **Descargar datos del escenario** desde **Evaluar rentabilidad** y carga ese segundo JSON. Guarda ambos archivos con cuidado: pueden contener términos de búsqueda e información comercial de tu cuenta.

## Alcance actual

Arbigen trabaja con una **muestra** de publicaciones, no con todo Mercado Libre. El índice de Google Trends es relativo y no equivale a demanda o ventas observadas. Por ahora, la categoría y el periodo que eliges al crear una investigación se guardan como contexto, pero no restringen automáticamente la consulta de productos; al importar Trends debes comprobar que el CSV corresponda al país y periodo que quieres estudiar. El Opportunity Score permanece como indicador exploratorio porque aún no se ha calibrado con ventas y competencia verificadas.

Según el país y la conexión disponible, algunas búsquedas pueden no devolver productos. Si no hay datos suficientes para un cálculo, la aplicación explica qué falta.

## Para desarrollar o instalar Arbigen

La [guía de desarrollo](docs/desarrollo.md) contiene los requisitos, los comandos para iniciar la aplicación y las pruebas. También puedes consultar la [arquitectura](docs/architecture.md), la [separación entre Development y Production](docs/entornos.md) y el [alcance del MVP](docs/release-mvp.md).
