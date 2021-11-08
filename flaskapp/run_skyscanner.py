from skyscannerAPI import run_skyscannerAPI 
import syslog

def main():
    try:
        result_heen = run_skyscannerAPI(reispersonen="1", land="NL", reisdatumheen="2022-05-29", reisbestemming="BER", aantalresultaten="10", reisvertrek="AMS")
        print(result_heen)
    except TypeError as e:
        print(e)
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_MAIL)
    
    # result_terug = run(reispersonen="1", land="GB", reisdatumheen="2022-06-01", reisdatumterug="2022-06-02", reisbestemming="AMS", aantalresultaten="10", reisvertrek="LHR")
    # print(result_terug)

main()

