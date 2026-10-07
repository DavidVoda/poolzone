import { useParams } from "react-router-dom"
import { ProductDetailForm } from "@/components/app/ProductDetailForm"

export default function ProductDetail() {
  const { id } = useParams()
  return <ProductDetailForm productId={Number(id)} variant="page" />
}
