import pandas as pd
import numpy as np
import logging

class FeatureEngineer:
    def __init__(self):
        self.logger = logging.getLogger("aether.features")
        
    def create_features(self, df_raw):
        """Create extended feature set including causal historical reliability."""
        self.logger.info("Starting feature engineering...")
        
        # 0. PIVOT DATA
        self.logger.info("Pivoting data to widespread format...")
        df_raw['initialization_time'] = pd.to_datetime(df_raw['initialization_time'])
        df_raw['valid_time'] = pd.to_datetime(df_raw['valid_time'])
        
        # We want to pivot 'source' -> 'forecast_value'
        index_cols = ['initialization_time', 'valid_time', 'lead_time', 'latitude', 'longitude', 'reference_value']
        
        df = df_raw.pivot(
            index=index_cols,
            columns='source',
            values='forecast_value'
        ).reset_index()
        
        df.columns.name = None
        
        # Ensure we have all candidates
        candidates = ['IFS', 'ICON', 'GFS']
        for c in candidates:
            if c not in df.columns:
                df[c] = np.nan
                
        # Drop rows where we miss predictions
        df = df.dropna(subset=candidates + ['reference_value']).reset_index(drop=True)
        
        df = df.sort_values(['initialization_time', 'valid_time', 'latitude', 'longitude']).reset_index(drop=True)
        
        # 1. Base disagreements
        self.logger.info("Computing instantaneous disagreement features...")
        df['disagreement_std'] = df[candidates].std(axis=1)
        df['disagreement_range'] = df[candidates].max(axis=1) - df[candidates].min(axis=1)
        df['diff_ifs_icon'] = np.abs(df['IFS'] - df['ICON'])
        df['diff_ifs_gfs'] = np.abs(df['IFS'] - df['GFS'])
        
        # 2. Temporal Encodes
        df['hour'] = df['valid_time'].dt.hour
        df['day_of_year'] = df['valid_time'].dt.dayofyear
        
        df['hour_sin'] = np.sin(2 * np.pi * df['hour']/24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour']/24)
        df['doy_sin'] = np.sin(2 * np.pi * df['day_of_year']/365)
        df['doy_cos'] = np.cos(2 * np.pi * df['day_of_year']/365)
        df['lead_time_sqrt'] = np.sqrt(df['lead_time'])
        
        # 3. CAUSAL HISTORICAL SKILL (NO LEAKAGE)
        self.logger.info("Computing causal historical features strictly pre-initialization...")
        
        # Initialize columns
        for c in candidates:
            df[f'{c}_recent_bias_3d'] = 0.0
            df[f'{c}_recent_mae_3d'] = 0.0
            df[f'{c}_recent_bias_7d'] = 0.0
            df[f'{c}_recent_mae_7d'] = 0.0
            
            # Location-specific
            df[f'{c}_recent_bias_3d_loc'] = 0.0
            df[f'{c}_recent_mae_3d_loc'] = 0.0
            
        unique_inits = sorted(df['initialization_time'].unique())
        
        for init_t in unique_inits:
            curr_mask = df['initialization_time'] == init_t
            if not curr_mask.any(): continue
            
            # purely historical observations available before this initialization
            hist_mask = df['valid_time'] < init_t
            df_hist = df[hist_mask]
            
            d3_mask = df_hist['valid_time'] >= (init_t - pd.Timedelta(days=3))
            d7_mask = df_hist['valid_time'] >= (init_t - pd.Timedelta(days=7))
            
            hist_3d = df_hist[d3_mask]
            hist_7d = df_hist[d7_mask]
            
            for c in candidates:
                # Global 3d / 7d
                if len(hist_3d) > 0:
                    bias_3d = np.mean(hist_3d[c] - hist_3d['reference_value'])
                    mae_3d = np.mean(np.abs(hist_3d[c] - hist_3d['reference_value']))
                else:
                    bias_3d, mae_3d = 0.0, 0.0
                    
                if len(hist_7d) > 0:
                    bias_7d = np.mean(hist_7d[c] - hist_7d['reference_value'])
                    mae_7d = np.mean(np.abs(hist_7d[c] - hist_7d['reference_value']))
                else:
                    bias_7d, mae_7d = 0.0, 0.0
                    
                df.loc[curr_mask, f'{c}_recent_bias_3d'] = bias_3d
                df.loc[curr_mask, f'{c}_recent_mae_3d'] = mae_3d
                df.loc[curr_mask, f'{c}_recent_bias_7d'] = bias_7d
                df.loc[curr_mask, f'{c}_recent_mae_7d'] = mae_7d
                
                # Spatial (Location-specific) rolling
                if len(hist_3d) > 0:
                    # grouped by lat lon
                    group_3d = hist_3d.groupby(['latitude', 'longitude'])
                    bias_3d_loc = group_3d.apply(lambda g: np.mean(g[c] - g['reference_value']))
                    mae_3d_loc = group_3d.apply(lambda g: np.mean(np.abs(g[c] - g['reference_value'])))
                    
                    # map back
                    def get_loc_metric(row, metric_series, default):
                        idx = (row.latitude, row.longitude)
                        return metric_series.get(idx, default)
                        
                    curr_df = df[curr_mask]
                    df.loc[curr_mask, f'{c}_recent_bias_3d_loc'] = curr_df.apply(lambda r: get_loc_metric(r, bias_3d_loc, bias_3d), axis=1)
                    df.loc[curr_mask, f'{c}_recent_mae_3d_loc'] = curr_df.apply(lambda r: get_loc_metric(r, mae_3d_loc, mae_3d), axis=1)
                else:
                    df.loc[curr_mask, f'{c}_recent_bias_3d_loc'] = 0.0
                    df.loc[curr_mask, f'{c}_recent_mae_3d_loc'] = 0.0
        
        self.logger.info("Feature engineering complete")
        return df
