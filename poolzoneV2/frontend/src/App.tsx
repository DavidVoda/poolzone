import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { AppShell } from "@/components/app/AppShell"
import Products from "@/pages/Products"
import ProductDetail from "@/pages/ProductDetail"
import Categories from "@/pages/Categories"
import Pricing from "@/pages/Pricing"
import Jobs from "@/pages/Jobs"

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <Products /> },
      { path: "/products/:id", element: <ProductDetail /> },
      { path: "/categories", element: <Categories /> },
      { path: "/pricing", element: <Pricing /> },
      { path: "/jobs", element: <Jobs /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
