import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Store, Search, MapPin, Users, Film, RefreshCw } from 'lucide-react'
import { adminService, AdminMerchantDetail } from '@/services/adminService'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

export const AdminMerchantDirectoryView: React.FC = () => {
  const [search, setSearch] = useState('')

  const { data: merchants = [], isLoading, refetch } = useQuery<AdminMerchantDetail[]>({
    queryKey: ['admin-merchants'],
    queryFn: () => adminService.listMerchants(),
  })

  const filtered = merchants.filter(
    (m) =>
      m.business_name.toLowerCase().includes(search.toLowerCase()) ||
      m.city.toLowerCase().includes(search.toLowerCase()) ||
      m.sector.toLowerCase().includes(search.toLowerCase())
  )

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Loading merchant directory...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 font-sans text-stone-900">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-stone-200">
        <div>
          <h2 className="text-xl font-extrabold text-stone-900 tracking-tight">Merchant Store Directory</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Registered storefronts across pilot cities (Nagpur / Mumbai).
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs font-bold gap-1.5">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh ({merchants.length})</span>
        </Button>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-stone-400 absolute left-3.5 top-3" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search stores by name, city, or sector..."
          className="w-full pl-10 pr-4 py-2 text-xs rounded-2xl border border-stone-200 bg-white focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white rounded-3xl border border-stone-200 p-12 text-center space-y-2 max-w-md mx-auto">
          <Store className="w-8 h-8 text-stone-400 mx-auto" />
          <h3 className="text-sm font-black text-stone-900">No stores match your search</h3>
          <p className="text-xs text-stone-500">Try searching for a different keyword or city name.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((m) => (
            <div
              key={m.id}
              className="bg-white rounded-3xl border border-stone-200/80 p-5 shadow-2xs space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-base font-black text-stone-900">{m.business_name}</h3>
                  <p className="text-xs text-stone-500 flex items-center gap-1 mt-0.5">
                    <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span>{m.address_text}, {m.city}</span>
                  </p>
                </div>
                {m.kyc_status === 'APPROVED' && <Badge variant="success">Approved</Badge>}
                {m.kyc_status === 'PENDING' && <Badge variant="amber">Pending</Badge>}
                {m.kyc_status === 'REJECTED' && <Badge variant="destructive">Rejected</Badge>}
              </div>

              <div className="flex items-center gap-3 pt-2 border-t border-stone-100 text-xs text-stone-500">
                <span className="flex items-center gap-1 font-mono">
                  <Film className="w-3.5 h-3.5 text-stone-400" />
                  {m.reels_count} deals
                </span>
                <span>•</span>
                <span className="flex items-center gap-1 font-mono">
                  <Users className="w-3.5 h-3.5 text-stone-400" />
                  {m.staff_count} cashiers
                </span>
                <span>•</span>
                <span className="font-mono text-[10px] text-stone-400">
                  Joined {new Date(m.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
