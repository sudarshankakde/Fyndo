import React from 'react'
import { Utensils, Sparkles, Smartphone, Layers } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { setSelectedSector } from '@/store/slices/uiSlice'
import { useTranslation } from '@/hooks/useTranslation'
import { cn } from '@/utils/cn'

export const SectorFilter: React.FC = () => {
  const dispatch = useAppDispatch()
  const { t } = useTranslation()
  const activeSector = useAppSelector((state) => state.ui.selectedSector)

  const sectors = [
    { id: null, label: t.filter_all, icon: Layers },
    { id: 'FOOD', label: t.filter_food, icon: Utensils },
    { id: 'FASHION', label: t.filter_fashion, icon: Sparkles },
    { id: 'ELECTRONICS', label: t.filter_electronics, icon: Smartphone },
  ]

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar select-none">
      {sectors.map((sec) => (
        <button
          key={sec.id ?? 'all'}
          onClick={() => dispatch(setSelectedSector(sec.id))}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 shrink-0 border',
            activeSector === sec.id
              ? 'bg-slate-100 text-slate-950 border-white font-bold shadow-md shadow-white/10 scale-105'
              : 'bg-slate-900/60 text-slate-400 border-slate-800/80 hover:border-slate-700 hover:text-slate-200'
          )}
        >
          <sec.icon className="h-3.5 w-3.5" />
          <span>{sec.label}</span>
        </button>
      ))}
    </div>
  )
}
