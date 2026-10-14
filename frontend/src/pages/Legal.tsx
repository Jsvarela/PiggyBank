import PublicPage from '../components/PublicPage'

const note =
  'Este texto describe cómo funciona esta app; es una plantilla informativa, no asesoría legal. Si vas a abrirla a otras personas, haz que un abogado la revise (en Colombia aplica la Ley 1581 de 2012 de protección de datos personales).'

export function Privacy() {
  return (
    <PublicPage title="Política de privacidad">
      <div className="space-y-4 text-sm leading-relaxed">
        <p>
          <b>Finanzas</b> es una app de finanzas personales. Quien la despliega y administra es la persona responsable de los datos que se guardan en esa instalación.
        </p>
        <section>
          <h2 className="font-semibold">Qué datos guarda</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>Tu correo y tu contraseña (la contraseña se guarda cifrada con argon2; nadie puede leerla).</li>
            <li>Lo que registras: cuentas, categorías, movimientos, presupuestos, metas y pagos recurrentes.</li>
            <li>Nunca pidas ni escribas números de tarjeta completos ni claves de tu banco en la app.</li>
          </ul>
        </section>
        <section>
          <h2 className="font-semibold">Dónde y cómo</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>En el servidor y la base de datos que eligió quien administra la instalación (por ejemplo Render y Neon), siempre por conexión cifrada (HTTPS).</li>
            <li>
              En tu dispositivo: una cookie de sesión (necesaria para mantenerte dentro; no se puede leer desde JavaScript), una copia local de tus cuentas y categorías, tu preferencia de tema y los movimientos
              que registres sin conexión hasta que se envíen.
            </li>
            <li>No hay publicidad, no se venden ni se comparten tus datos.</li>
          </ul>
        </section>
        <section>
          <h2 className="font-semibold">Correo, errores y estadísticas</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>El correo solo se usa para confirmar tu dirección y recuperar tu contraseña.</li>
            <li>Si algo falla en tu navegador, el mensaje técnico y la ruta de la pantalla se guardan en el registro del servidor. No incluyen tus montos ni descripciones.</li>
            <li>Las estadísticas de uso están apagadas por defecto. Si quien administra las enciende (GoatCounter, sin cookies), solo cuentan qué pantalla se visita, nunca datos financieros.</li>
          </ul>
        </section>
        <section>
          <h2 className="font-semibold">Tus derechos</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>Descargar todo: <b>Más → Respaldo y exportación</b> (JSON y CSV).</li>
            <li>Borrar todo: <b>Más → Cuenta → Eliminar cuenta</b>. Se elimina de inmediato; las copias internas del proveedor de la base de datos pueden tardar unas horas en rotar.</li>
          </ul>
        </section>
        <p className="text-xs text-slate-500">{note}</p>
      </div>
    </PublicPage>
  )
}

export function Terms() {
  return (
    <PublicPage title="Términos de uso">
      <div className="space-y-4 text-sm leading-relaxed">
        <section>
          <h2 className="font-semibold">Qué es y qué no es</h2>
          <p>Finanzas te ayuda a llevar el control de tu dinero. No es asesoría financiera, contable ni tributaria, ni se conecta a tu banco: los saldos salen de lo que tú registras.</p>
        </section>
        <section>
          <h2 className="font-semibold">Uso</h2>
          <ul className="list-disc space-y-1 pl-5">
            <li>Es una app de uso personal. Eres responsable de la veracidad de lo que registras y de cuidar tu contraseña.</li>
            <li>No la uses para actividades ilegales ni para intentar acceder a datos de otras personas.</li>
          </ul>
        </section>
        <section>
          <h2 className="font-semibold">Sin garantías</h2>
          <p>
            La app se ofrece «tal cual», sin garantía de disponibilidad. Los servicios gratuitos pueden dormir, cambiar o desaparecer. Por eso conviene descargar un respaldo de vez en cuando (Más → Respaldo y exportación):
            quien administra la app no responde por datos perdidos.
          </p>
        </section>
        <section>
          <h2 className="font-semibold">Tu cuenta</h2>
          <p>Puedes eliminarla cuando quieras desde Más → Cuenta. Al hacerlo se borran todos tus datos y no se pueden recuperar.</p>
        </section>
        <section>
          <h2 className="font-semibold">Cambios</h2>
          <p>Estos términos pueden actualizarse; la versión vigente es la que se ve en esta página.</p>
        </section>
        <p className="text-xs text-slate-500">{note}</p>
      </div>
    </PublicPage>
  )
}
