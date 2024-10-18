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
