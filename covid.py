# -*- coding: utf-8 -*-
"""
Created on Sun Apr 19 17:28:12 2020

@author: Mei Eisenbach
"""
import sys
import pandas as pd
import geopandas as gpd
from geopy.geocoders import ArcGIS
from geopy.extra.rate_limiter import RateLimiter
from shapely.geometry import Point

def geo_code(df):
    df_new = df.copy()
    lookup = df.Address+', '+df.City+', '+df.State+' '+df.Zip.map(str)
    try:
        geolocator = ArcGIS()
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=.1)
        df_new['location'] = lookup.apply(geocode)
    except:
        print('Error geocoding addresses. Aborting script')
        sys.exit()
    
    df_new['addr_found'] = df_new['location'].map(lambda a: a.address)
    df_new['Longitude'] = df_new['location'].map(lambda a: a.longitude)
    df_new['Latitude'] = df_new['location'].map(lambda a: a.latitude)
    df_new['score'] = df_new['location'].map(lambda a: a.raw['score'])
    
    return df_new

def convert_to_gdf(df):
    geom = df.apply(lambda a : Point([a['Longitude'], a['Latitude']]), axis=1)
    gdf = gpd.GeoDataFrame(df_new, geometry=geom)
    gdf.crs = {'init' :'epsg:4326'}
    return gdf

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('SYNTAX: python covid.py yesterday_file today_file')
        sys.exit()
    
    yesterday = sys.argv[1]
    today = sys.argv[2]
    output = 'output.txt'
    tobechecked = 'tobechecked.txt'
    santa_rita = '5325 Broder Blvd'
    
    # Read in all needed files
    df_yesterday = pd.read_csv(yesterday, sep='\t')
    print('{} record(s) read from {}'.format(df_yesterday.shape[0], yesterday))
    
    df_today = pd.read_csv(today, sep='\t')
    print('{} record(s) read from {}'.format(df_today.shape[0], today))

    gdf_boundaries = gpd.read_file('geocoding/PL18_Esri_Hayward_WGS84.shp')

    # set indices
    df_yesterday.set_index('IncidentID', inplace=True)
    df_today.set_index('IncidentID', inplace=True)

    # new rows are indices in today's which are not in yesterday's
    new_rows = ~df_today.index.isin(df_yesterday.index)
    print('{} new record(s) found'.format(df_today[new_rows].shape[0]))    

    print('Geocoding new records...')    
    df_new = geo_code(df_today[new_rows])
    
    # separate rows with score <100
    check = df_new.score < 100
    df_check = df_new[check]
    df_new.drop(df_check.index, inplace=True)
    
    # do spatial join
    gdf_new = convert_to_gdf(df_new)
    gdf_joined = gpd.sjoin(gdf_new, gdf_boundaries, op='within')

    # change PL2018 to "Santa Rita Jail" if address matches
    gdf_joined.loc[gdf_joined.Address == santa_rita, 'PL2018'] = 'Santa Rita Jail'

    # merge new rows with yesterday's    
    df_out = pd.concat([df_yesterday, gdf_joined.drop(columns=['location', 'geometry', 'index_right'])])    
    df_out.to_csv(output, sep='\t')
    print('Merged data written to {}'.format(output))
    
    df_check.to_csv(tobechecked, sep='\t')
    print('{} record(s) written to {}'.format(df_check.shape[0], tobechecked))        
