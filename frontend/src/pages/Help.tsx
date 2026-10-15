const topics: [string, string[]][] = [
  [
    'Apuntar un gasto o un ingreso',
    [
      'Toca el botón verde «+» (abajo a la derecha, en cualquier pantalla).',
      'Elige si es Gasto, Ingreso o Transferencia, escribe el monto y elige la categoría y la cuenta.',
      'Para no teclear: toca los botones +1.000, +5.000, +10.000… y el monto se va sumando. «Borrar monto» lo deja en cero.',
      'Toca Guardar. Si no hay internet, queda guardado y se envía solo cuando vuelva.',
    ],
  ],
  [
    'Inicio',
    ['Muestra cuánto tienes en total, cuánto has ganado y gastado este mes, tus cuentas y los últimos movimientos.', 'Si un presupuesto se está acabando, aquí aparece un aviso.'],
  ],
  [
    'Movimientos',
    ['La lista de todo lo que has apuntado. Puedes buscar y filtrar por fecha, cuenta o categoría.', 'Toca un movimiento para corregirlo o borrarlo.'],
  ],
  [
    'Presupuestos',
    ['Pon un límite de gasto por categoría (por ejemplo, «Comida: $ 500.000 al mes»).', 'La barra te muestra cuánto llevas y cuánto te queda. Se pone amarilla al acercarte y roja si te pasas.'],
  ],
  [
    'Metas de ahorro',
    ['Crea una meta (un viaje, un celular, un fondo de emergencia) con el monto que quieres juntar y, si quieres, una fecha.', 'Con «Aportar» pasas plata de una cuenta a la meta. La app te sugiere cuánto ahorrar cada mes.'],
  ],
  [
    'Préstamos',
    [
      'Sirve para anotar el dinero que le prestaste a alguien: a quién, cuánto prestaste, cuánto esperas recibir y en qué fecha.',
      'Cuando te paguen, toca «Ya me pagó». Los vencidos se marcan en rojo.',
      'Es solo un recordatorio: no cambia los saldos de tus cuentas.',
    ],
  ],
  [
    'Cuentas',
    ['Una cuenta es donde tienes tu plata: efectivo, un banco, Nequi, una tarjeta… (Más → Cuentas).', 'El saldo se calcula solo con lo que apuntas. Si no cuadra con tu banco, revisa que no falte algún movimiento.'],
  ],
  [
    'Transferencias',
    ['Mover plata entre tus propias cuentas (por ejemplo, del banco al efectivo) se apunta como «Transferencia».', 'No cuenta como gasto ni como ingreso, solo cambia de lugar.'],
  ],
  [
    'Pagos que se repiten',
    ['En Más → Recurrentes anotas lo que pagas o recibes cada cierto tiempo: arriendo, Netflix, salario.', 'La app crea esos movimientos sola cuando llega la fecha y te muestra los próximos pagos.'],
  ],
  [
    'Importar del banco',
    ['En Más → Importar extracto puedes subir el archivo CSV que te da tu banco, ver cómo quedaría y confirmar. Los repetidos se detectan.'],
  ],
  [
    'Respaldo y seguridad',
    [
      'En Más → Respaldo puedes descargar todos tus datos. Hazlo de vez en cuando: es tu copia de seguridad.',
      'En Más → Cuenta cambias tu contraseña, cierras sesiones o borras tu cuenta (se borra todo, no se puede deshacer).',
      'Nadie más en la app ve tus datos: cada persona tiene los suyos.',
    ],
  ],
  [
    'Usar la app como si fuera una aplicación del celular',
    ['En la pantalla Más aparece la opción de instalarla en tu pantalla de inicio. Así se abre sin buscarla en el navegador.', 'Para que la app quede abierta sin pedir tu clave cada vez, no cierres sesión con «Salir».'],
  ],
]

export default function Help() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">Guía rápida. Toca un tema para ver cómo se hace.</p>
      <div className="divide-y rounded-xl bg-surface px-4 shadow-sm">
        {topics.map(([title, steps]) => (
          <details key={title} className="group py-3">
            <summary className="cursor-pointer list-none font-medium after:float-right after:text-slate-400 after:content-['+'] group-open:after:content-['–']">{title}</summary>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </details>
        ))}
      </div>
    </div>
  )
}
