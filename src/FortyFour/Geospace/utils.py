import geopandas as gpd
from shapely.geometry import Point, Polygon
import pandas as pd

def create_polygon_from_point_list(df:pd.DataFrame, crs:int, convert_to_latlon:bool=True) -> gpd.GeoDataFrame:
    """_summary_

    Args:
        df (pd.DataFrame): This is a dataframe with the following fields : (lat,lon) or (X,Y)
        crs (int, optional): The crs of the data source.
        convert_to_latlon (bool, optional): If true, it will convert UTM to Lon/Lat. Defaults to True.

    Returns:
        _type_: The function returns a GeodataFrame
    """

    try:
        points_array = gpd.points_from_xy(df['X'], df['Y'])
    except Exception as e:
        points_array = gpd.points_from_xy(df['lon'], df['lat'])
        
    poly = Polygon([[p.x, p.y] for p in points_array])
    data = {'code': ['NA'], 'geometry': poly}
    gdf = gpd.GeoDataFrame(data, crs=f"epsg:{crs}")
    if convert_to_latlon:
        gdf.to_crs(4326, inplace=True)
    return gdf


def get_area_of_polygons(gdf=gpd.GeoDataFrame, unit:str="km") -> gpd.GeoDataFrame:

    gdf.to_crs(4326, inplace=True) # Always convert into lon/lat format for more accuracy
    gdf["centroid_lon"] = gdf.centroid.x
    gdf["centroid_lat"] = gdf.centroid.y
    # chose the first polygon in the geodatafram as reference: (this is not perfect but it approximate well)
    center_lat = gdf.iloc[0]["centroid_lat"]
    center_lon = gdf.iloc[0]["centroid_lon"]

    match unit:
        case "km":
            gdf = gdf.to_crs(f"+proj=cea +lat_0={center_lat} +lon_0={center_lon} +units=km")
            gdf["area_km2"] = gdf.area.round(0)
        case default:
            gdf = gdf.to_crs(f"+proj=cea +lat_0={center_lat} +lon_0={center_lon} +units=m")
            gdf["area_m2"] = gdf.area.round(0)
    return gdf
