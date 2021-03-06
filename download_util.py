import time
import os
from obspy.clients.fdsn.mass_downloader import GlobalDomain, \
        Restrictions, MassDownloader


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        dt = te - ts
        print("%r  %2.2f s" % (method.__name__, dt))
        return {"result": result, "time": dt}
    return timed


def safe_mkdir(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def get_event_time(event):
    origin = event.preferred_origin()
    return origin.time


def list2str(val):
    if isinstance(val, list):
        res = ",".join(val)
    elif val == "None" or val is None:
        res = None
    else:
        raise ValueError("Unknown type: {}".format(val))
    return res


def download_global_data(
        starttime,
        endtime,
        waveform_dir,
        stationxml_dir,
        stations=None,
        networks=None,
        channels=None,
        location_priorities=None,
        channel_priorities=None,
        minimum_length=0.95,
        reject_channels_with_gaps=True,
        providers=None):

    domain = GlobalDomain()

    station = list2str(stations)
    network = list2str(networks)
    channel = list2str(channels)

    print("network {}: | station: {} | channel: {} ".format(
        network, station, channel))

    time.sleep(2.0)

    # Set download restrictions
    restrictions = Restrictions(
        starttime=starttime,
        endtime=endtime,
        reject_channels_with_gaps=reject_channels_with_gaps,
        minimum_length=minimum_length,
        station=station,
        network=network,
        channel=channel,
        location_priorities=location_priorities,
        channel_priorities=channel_priorities
    )

    if (providers is None) or (providers == "None"):
        mdl = MassDownloader()
    else:
        mdl = MassDownloader(providers=providers)

    mdl.download(domain, restrictions,
                 mseed_storage=waveform_dir,
                 stationxml_storage=stationxml_dir)


@timeit
def download_event(eventname, event, params,
                   waveform_base, station_base):
    # Request config_file
    event_time = get_event_time(event)

    obsd_dir = os.path.join(waveform_base, eventname)
    safe_mkdir(obsd_dir)
    stationxml_dir = os.path.join(station_base, eventname)
    safe_mkdir(stationxml_dir)

    starttime = event_time + params["starttime_offset"]
    endtime = event_time + params["endtime_offset"]

    print("Event time:   ", event_time)
    print("download time: {} --> {}".format(starttime, endtime))
    print("providers: ", params["providers"])

    # Get station_list from station_file in database entry
    download_global_data(
        starttime, endtime,
        obsd_dir, stationxml_dir,
        networks=params["networks"],
        stations=params["stations"],
        channels=params["channels"],
        location_priorities=params["location_priorities"],
        channel_priorities=params["channel_priorities"],
        providers=params["providers"])


@timeit
def convert_event(eventname, waveform_base, station_base, asdf_base):
    from pyasdf import ASDFDataSet
    from pypers import Space
    from obspy import read, read_inventory, read_events

    ws = Space(os.path.join(waveform_base, eventname))
    safe_mkdir(asdf_base)

    with ASDFDataSet(os.path.join(asdf_base, eventname + '.raw_obs.h5'), mode='w',
        mpi=False, compression=None) as ds:
        try:
            ds.add_quakeml(read_events('CMT/CMT.190/' + eventname))
        
        except Exception as e:
            print(e)

        stations = set()

        for wav in ws.ls():
            station = '.'.join(wav.split('.')[:2])
            stations.add(station)

            try:
                ds.add_waveforms(read(ws[wav]), 'raw_obs')
            
            except:
                pass
        
        for station in stations:
            try:
                ds.add_stationxml(os.path.join(station_base, eventname, station + '.xml'))
            
            except Exception as e:
                print(e)
