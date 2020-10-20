#!/usr/bin/env bash

docker rm -f ndm_cdc_1 ndm_dfc_1 ndm_kc_1 ndm_mp4sim_1 ndm_mp4pixhawk_1 ndm_sim_1 ndm_mpa_1 
docker rm -f ndm_cdg_1
docker rmi -f ndm_cdc ndm_ws ndm_kc ndm_sim ndm_mp
docker rmi -f ndm_cdg
