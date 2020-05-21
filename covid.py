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

# Constants
santa_rita_jail = '5325 Broder Blvd'
shapefile = 'geocoding/PL18_Esri_Hayward_WGS84.shp'
output = 'output.txt'
tobechecked = 'tobechecked.txt'

def load_files(done, today, shapefile, output, tobechecked):
    df_done = pd.read_csv(done, sep='\t')
    print('{} record(s) read from {}'.format(df_done.shape[0], done))
    
    df_today = pd.read_csv(today, sep='\t')
    print('{} record(s) read from {}'.format(df_today.shape[0], today))

    gdf_boundaries = gpd.read_file(shapefile)

    # Set indices
    df_done.set_index('IncidentID', inplace=True)
    df_today.set_index('IncidentID', inplace=True)

    return df_done, df_today, gdf_boundaries
    
def geocode(df):
    df_new = df.copy()
    lookup = df.Address+', '+df.City+', '+df.State+' '+df.Zip.map(str)
    try:
        geolocator = ArcGIS()
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=.1)
        df_new['location'] = lookup.apply(geocode)
    except:
        print('Error geocoding addresses. Aborting script')
        sys.exit()
    
    # Handle rows where geocoding failed
    failed = df_new['location'].isna()
    df_failed = df_new[failed]
    df_new.drop(df_failed.index, inplace=True)    
    
    df_new['MyZip'] = df_new['location'].map(lambda a: a.address.split(', ')[-1])
    df_new['MyX'] = df_new['location'].map(lambda a: a.longitude)
    df_new['MyY'] = df_new['location'].map(lambda a: a.latitude)
    df_new['Match_addr'] = df_new['location'].map(lambda a: a.address)
    df_new['Score'] = df_new['location'].map(lambda a: a.raw['score'])

    # Separate rows with score <100
    check = df_new.Score < 100
    df_check = df_new[check].drop(columns=['location'])
    df_new.drop(df_check.index, inplace=True)
    
    df_new.rename(columns={'Address':'Done_Address', 'AptNo':'Done_AptNo', 
                     'City':'Done_City', 'State':'Done_State', 'Zip':'Done_Zip'}, inplace=True)
    return df_new, df_check, df_failed

def convert_to_gdf(df):
    geom = df.apply(lambda a : Point([a['MyX'], a['MyY']]), axis=1)
    gdf = gpd.GeoDataFrame(df, geometry=geom)
    gdf.crs = 'epsg:4326'
    return gdf

def spatial_join(df):
    gdf = convert_to_gdf(df)
    gdf_joined = gpd.sjoin(gdf, gdf_boundaries, op='within')
    gdf_joined.rename(columns={'PL2018':'Place'}, inplace=True)
    return gdf_joined

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('SYNTAX: python covid.py done_file today_file')
        sys.exit()
     
    done = sys.argv[1]
    today = sys.argv[2]
    
    df_done, df_today, gdf_boundaries = load_files(done, today, shapefile, output, tobechecked)

    # Generate masks for the old and new rows
    old_rows = df_today.index.isin(df_done.index)
    new_rows = ~old_rows
    num_new = new_rows.sum()
    print('{} new record(s) found'.format(num_new))    

    # Get indexes of rows with address changes
    address_changed = df_done.loc[df_today[old_rows].index].Done_Address != df_today[old_rows].Address
    num_changed = address_changed.sum()
    print('{} address(es) with changes'.format(num_changed))

    df_out = df_done.copy()
    df_check = pd.DataFrame()

    cols = ['Done_Address', 'Done_AptNo', 'Done_City', 'Done_State', 'Done_Zip', 
            'MyZip', 'MyX', 'MyY', 'Match_addr', 'Score', 'Place']
    
    # Handle new records
    if num_new > 0:    
        print('Geocoding new records...')    
        df_new, df_check, df_failed = geocode(df_today[new_rows])

        gdf_new = spatial_join(df_new)

        # Append new rows with done's
        df_out = pd.concat([df_out, gdf_new[cols]])

        if len(df_failed) > 0:
            print('Unable to geocode {} new record(s)'.format(len(df_failed)))
    # Handle changed records        
    if num_changed > 0:
        print('Geocoding changed records...')    
        df_changed, df_changed_check, df_changed_failed = geocode(df_today.loc[address_changed.index])
        df_check = pd.concat([df_check, df_changed_check])
    
        gdf_changed = spatial_join(df_changed)
    
        # Replace changed rows with done
        df_out = pd.concat([df_out.drop(index=gdf_changed.index), gdf_changed[cols]])

        if len(df_failed) > 0:
            print('Unable to geocode {} new record(s)'.format(len(df_failed)))
                        
    # Change Place to "Santa Rita Jail" if address matches
    df_out.loc[df_out.Done_Address == santa_rita_jail, 'Place'] = 'Santa Rita Jail'

    df_out.to_csv(output, sep='\t')
    print('Merged data written to {}'.format(output))    

    df_check.to_csv(tobechecked, sep='\t')
    print('{} record(s) written to {}'.format(df_check.shape[0], tobechecked))        
