import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Compass, Store, QrCode, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface NotFoundPageProps {
  area?: 'shopper' | 'merchant' | 'pos' | 'admin'
}

export const NotFoundPage: React.FC<NotFoundPageProps> = ({ area }) => {
  const location = useLocation()

  const detectedArea =
    area ||
    (location.pathname.startsWith('/pos')
      ? 'pos'
      : location.pathname.startsWith('/admin')
      ? 'admin'
      : location.pathname.startsWith('/merchant')
      ? 'merchant'
      : 'shopper')

  const getAreaConfig = () => {
    switch (detectedArea) {
      case 'pos':
        return {
          icon: <QrCode className="w-8 h-8 text-emerald-600" />,
          title: 'Terminal Page Not Found',
          description: 'The requested cashier terminal action or screen does not exist.',
          target: '/pos',
          label: 'Return to Counter Scanner',
        }
      case 'admin':
        return {
          icon: <ShieldAlert className="w-8 h-8 text-stone-700" />,
          title: 'Admin Page Not Found',
          description: 'The requested administrative view does not exist or has been relocated.',
          target: '/admin',
          label: 'Return to Admin Desk',
        }
      case 'merchant':
        return {
          icon: <Store className="w-8 h-8 text-amber-600" />,
          title: 'Store Studio Page Not Found',
          description: 'The merchant tool or offer screen you are looking for does not exist.',
          target: '/merchant',
          label: 'Return to Store Studio',
        }
      default:
        return {
          icon: <Compass className="w-8 h-8 text-primary" />,
          title: 'Deal Page Not Found',
          description: 'The discount offer or page you are looking for does not exist or was moved.',
          target: '/',
          label: 'Return to Deals Feed',
        }
    }
  }

  const config = getAreaConfig()

  return (
    <div className="min-h-[60vh] bg-[#FAFAFA] flex flex-col items-center justify-center p-6 text-center font-sans text-stone-900">
      <div className="w-16 h-16 rounded-3xl bg-white border border-stone-200/80 shadow-xs flex items-center justify-center mb-4">
        {config.icon}
      </div>
      <h1 className="text-2xl font-black text-stone-900 tracking-tight">{config.title}</h1>
      <p className="text-xs text-stone-500 max-w-sm mt-1 mb-6 leading-relaxed">
        {config.description}
      </p>
      <Link to={config.target}>
        <Button variant="primary" className="text-xs font-bold">
          {config.label}
        </Button>
      </Link>
    </div>
  )
}
