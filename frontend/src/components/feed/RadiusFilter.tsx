import React from 'react'
import { MapPin } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { setRadiusKm } from '@/store/slices/uiSlice'
import { useTranslation } from '@/hooks/useTranslation'
import { cn } from '@/utils/cn'

export const RadiusFilter: React.FC = () => {
  const dispatch = useAppDispatch()
  const { t } = useTranslation()
  const activeRadius = useAppSelector((state) => state.ui.radiusKm)

  const radiusOptions = [
    { km: 2, label: t.radius_2km },
    { km: 5, label: t.radius_5km },
    { km: 10, label: t.radius_10km },
  ]

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar select-none">
      <div className="flex items-center gap-1 text-slate-400 text-xs font-semibold px-1">
        <MapPin className="h-3.5 w-3.5 text-amber-400" />
        <span>Radius:</span>
      </div>
      {radiusOptions.map((opt) => (
        <button
          key={opt.km}
          onClick={() => dispatch(setRadiusKm(opt.km))}
          className={cn(
            'px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 shrink-0 border',
            activeRadius === opt.km
              ? 'bg-amber-500 text-slate-950 border-amber-400 font-bold shadow-md shadow-amber-500/20 scale-105'
              : 'bg-slate-900/80 text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
