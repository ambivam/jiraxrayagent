Feature: Gestión de la lista de tareas
  Como usuario
  Quiero gestionar mis tareas
  Para poder llevar un seguimiento de mis pendientes

  Scenario: Crear una nueva tarea
    Dado que estoy en la aplicación de tareas
    Cuando ingreso una nueva tarea "Comprar víveres"
    Y hago clic en el botón de agregar
    Entonces debería ver "Comprar víveres" en la lista de tareas

  Scenario: Marcar una tarea como completada
    Dado que tengo una tarea "Comprar víveres"
    Cuando hago clic en la casilla junto a "Comprar víveres"
    Entonces la tarea "Comprar víveres" debería estar marcada como completada

  Scenario: Editar una tarea existente
    Dado que tengo una tarea "Comprar víveres"
    Cuando hago doble clic en "Comprar víveres"
    Y cambio el texto a "Comprar víveres orgánicos"
    Y presiono Enter
    Entonces debería ver "Comprar víveres orgánicos" en la lista de tareas

  Scenario: Eliminar una tarea
    Dado que tengo una tarea "Comprar víveres"
    Cuando paso el cursor sobre "Comprar víveres"
    Y hago clic en el botón de eliminar
    Entonces "Comprar víveres" debería eliminarse de la lista de tareas

  Scenario: Filtrar tareas activas
    Dado que tengo las siguientes tareas:
      | Tarea               | Estado    |
      | Comprar víveres      | completada |
      | Limpiar la casa      | activa     |
      | Pagar facturas       | activa     |
    Cuando hago clic en el filtro "Activas"
    Entonces solo debería ver las tareas activas
    Y debería ver 2 tareas en la lista

  Scenario: Limpiar tareas completadas
    Dado que tengo algunas tareas completadas
    Cuando hago clic en "Limpiar completadas"
    Entonces todas las tareas completadas deberían eliminarse
    Y solo deberían quedar las tareas activas en la lista
