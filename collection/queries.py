def get_sid_query():
    return """
        query ShopInfoCore($id: Int!, $domain: String) {
          shopInfoByID(input: {shopIDs: [$id], fields: ["core"], domain: $domain, source: "shoppage"}) {
            result {
              shopCore {
                description
                domain
                shopID
                name
                tagLine
                defaultSort
              }
            }
            error {
              message
            }
          }
        }
        """


def get_product_query():
    return """
            query ShopProducts($sid: String!, $source: String, $page: Int, $perPage: Int, $keyword: String, $etalaseId: String, $sort: Int, $user_districtId: String, $user_cityId: String, $user_lat: String, $user_long: String) {
              GetShopProduct(shopID: $sid, source: $source, filter: {page: $page, perPage: $perPage, fkeyword: $keyword, fmenu: $etalaseId, sort: $sort, user_districtId: $user_districtId, user_cityId: $user_cityId, user_lat: $user_lat, user_long: $user_long}) {
                status
                errors
                links {
                  prev
                  next
                }
                data {
                  name
                  product_url
                  product_id
                  price {
                    text_idr
                  }
                }
              }
            }
            """


def get_product_details_query():
    return """
            query PDPGetLayoutQuery($shopDomain: String, $productKey: String, $layoutID: String, $apiVersion: Float, $userLocation: pdpUserLocation, $extParam: String, $tokonow: pdpTokoNow, $deviceID: String) {
              pdpGetLayout(shopDomain: $shopDomain, productKey: $productKey, layoutID: $layoutID, apiVersion: $apiVersion, userLocation: $userLocation, extParam: $extParam, tokonow: $tokonow, deviceID: $deviceID) {
                basicInfo {
                id: productID
                shopID
                shopName
                url
                category {
                    id
                    name
                    title
                    breadcrumbURL
                    detail {
                    id
                    name
                    breadcrumbURL
                    }
                  }
                }
                components {
                data {
                    ...ProductMedia
                    ...ProductHighlight
                    ...ProductDetail
                    ...ProductVariant
                  }
                }
              }
            }

            fragment ProductMedia on pdpDataProductMedia {
            media {
                urlMaxRes: URLMaxRes
              }
            }

            fragment ProductHighlight on pdpDataProductContent {
            name
            price {
                value
                currency
                priceFmt
                slashPriceFmt
                discPercentage
              }
            }

            fragment ProductDetail on pdpDataProductDetail {
            content {
                title
                subtitle
                applink
                showAtFront
                isAnnotation
              }
            }

            fragment ProductVariant on pdpDataProductVariant {
            parentID
            defaultChild
            children {
                productID
                price
                optionID
                optionName
                productName
                productURL
              }
            }
            """
