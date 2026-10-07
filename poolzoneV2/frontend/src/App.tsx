import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { AppShell } from "@/components/app/AppShell"
import Products from "@/pages/Products"
import ProductDetail from "@/pages/ProductDetail"
import Categories from "@/pages/Categories"
import FeedMapping from "@/pages/FeedMapping"
import Feeds from "@/pages/Feeds"
import Pricing from "@/pages/Pricing"
import Jobs from "@/pages/Jobs"
import FeatureRequests from "@/pages/FeatureRequests"
import Users from "@/pages/Users"
import Login from "@/pages/Login"
import { useMe } from "@/lib/auth"

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <Products /> },
      { path: "/products/:id", element: <ProductDetail /> },
      { path: "/categories", element: <Categories /> },
      { path: "/feed-mapping", element: <FeedMapping /> },
      { path: "/feeds", element: <Feeds /> },
      { path: "/pricing", element: <Pricing /> },
      { path: "/jobs", element: <Jobs /> },
      { path: "/feature-requests", element: <FeatureRequests /> },
      { path: "/users", element: <Users /> },
    ],
  },
])

export default function App() {
  const { data: me, isLoading } = useMe()
  if (isLoading) return null
  // Production requires a session; dev leaves auth_required false → app is open.
  if (me?.auth_required && !me.user) return <Login />
  return <RouterProvider router={router} />
}
