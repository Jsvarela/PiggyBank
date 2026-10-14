import { Link } from 'react-router-dom'
import { useConfig, useMe } from '../api/hooks'

/** Recordatorio de confirmar el correo; solo aparece si esta instalación puede enviar correos. */
export default function VerifyBanner() {
  const user = useMe().data
  const emailEnabled = useConfig().data?.email_enabled
  if (!user || user.email_verified || !emailEnabled) return null
  return (
    <Link to="/cuenta" className="block rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
      Confirma tu correo para poder recuperar tu contraseña si la olvidas. Toca aquí.
    </Link>
  )
}
