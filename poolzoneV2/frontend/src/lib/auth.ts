import { useQuery, useQueryClient } from "@tanstack/react-query"
import { client, unwrap, type Me } from "@/lib/api"

/** Current auth state: whether login is required, and who (if anyone) is in. */
export function useMe() {
  return useQuery<Me>({
    queryKey: ["me"],
    queryFn: () => unwrap(client.GET("/api/auth/me")),
    staleTime: 30_000,
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return async () => {
    await client.POST("/api/auth/logout")
    // Reset everything: a different user must not see the previous one's cached data.
    qc.clear()
  }
}
