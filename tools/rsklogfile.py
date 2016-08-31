import parse
import json
import argparse
import sys
import ast
import time
from openpyxl import Workbook
from datetime import datetime
from collections import OrderedDict as odict

parser = argparse.ArgumentParser()
parser.add_argument('logFile', help='log filename')
parser.add_argument('-o', '--output', help='Raw output log operations (XLS format)')
parser.add_argument('-c', '--complete', help='Emit ckpool-like log (Y) or complete event information (default)')
parser.add_argument('-r', '--rskmode', help='Log RSK plugin (Y) or unmodified Stratum Mining (default)')
parser.add_argument('-d', '--debug', help='Debug mode (Y)')
parser.add_argument('-n', '--notify', help='Adds miner notification functionality (Y)')
args = parser.parse_args()

def delta_ms(start, finish):
    delta = finish - start
    return delta * 1000.0

class RSKParser:
    def __init__(self, filename, output, mode, complete, debug, notify):
        self.filename = filename
        self.complete = True if complete == "Y" else False
        self.debug = True if debug == "Y" else False
        self.output = open(output, "w+") if output else None
        self.notify = True if notify == "Y" else False
        self.error_output = open("error.log", "w+") if "error.log" else None
        self.rskmode = True if mode == "Y" else False
        self.rsk_block_received_event = []
        self.rsk_block_received_start = []
        self.rsk_block_received_templ = []
        self.rsk_block_received_end   = []
        self.btc_block_received_event = []
        self.btc_block_received_start = []
        self.btc_block_received_templ = []
        self.btc_block_received_end   = []
        self.share_received_start     = []
        self.share_received_hex       = []
        self.rsk_submitblock          = []
        self.btc_submitblock          = []
        self.line_count = 1
        self.dumping_conf             = True
        self.confpy                   = []
        self.swb = Workbook()
        self.sws = self.swb.create_sheet()
        self.sws.title = "rsk-str-merge-mining-summary"
        self.sws_rowcount = 1
        if self.complete:
            if self.rskmode:
                if self.debug:
                    self.swb_rbrs = self.swb.create_sheet()
                    self.swb_rbrs.title = "RSK Block Received - Start"
                    self.swb_rbre = self.swb.create_sheet()
                    self.swb_rbre.title = "RSK Block Received - End"
                    self.swb_rbrt = self.swb.create_sheet()
                    self.swb_rbrt.title = "RSK Block Received - Template"
                    self.swb_rsb = self.swb.create_sheet()
                    self.swb_rsb.title = "RSK Submitblock"
                self.swb_rbrev = self.swb.create_sheet()
                self.swb_rbrev.title = "RSK Block Received Event"
                self.swb_rnbp = self.swb.create_sheet()
                self.swb_rnbp.title = "RSK New Block Parent"
                self.swb_rnwu = self.swb.create_sheet()
                self.swb_rnwu.title = "RSK New Work Unit"
            if self.debug:
                self.swb_bbrs = self.swb.create_sheet()
                self.swb_bbrs.title = "BTC Block Received - Start"
                self.swb_bbre = self.swb.create_sheet()
                self.swb_bbre.title = "BTC Block Received - End"
                self.swb_bbrt = self.swb.create_sheet()
                self.swb_bbrt.title = "BTC Block Received - Template"
                self.swb_srs = self.swb.create_sheet()
                self.swb_srs.title = "Share Received - Start"
                self.swb_srh = self.swb.create_sheet()
                self.swb_srh.title = "Share Received - Hex"
                self.swb_sb = self.swb.create_sheet()
                self.swb_sb.title = "Submitblock End"
                self.swb_bsb = self.swb.create_sheet()
                self.swb_bsb.title = "BTC Submitblock"
            self.swb_bbrev = self.swb.create_sheet()
            self.swb_bbrev.title = "BTC Block Received Event"
            self.swb_bnbp = self.swb.create_sheet()
            self.swb_bnbp.title = "BTC New Block Parent"
            self.swb_bnwu = self.swb.create_sheet()
            self.swb_bnwu.title = "BTC New Work Unit"
            self.swb_ws = self.swb.create_sheet()
            self.swb_ws.title = "Work Sent"
            self.swb_wso = self.swb.create_sheet()
            self.swb_wso.title = "Work Sent (Old)"
            self.swb_process = self.swb.create_sheet()
            self.swb_process.title = "CPU MEM %"
        if self.notify:
            self.swb_notify = self.swb.create_sheet()
            self.swb_notify.title = "mining.notify"
            self.notify_events = []
            self.curr_notify_id = ""

    def parse(self):
        # A logged line can contain a '\n', so we join them before parsing
        with open(self.filename, "r") as f:
            for line in f:
                sys.stdout.write("Parsing line number %d, excel row %d   \r" % (self.line_count, self.sws_rowcount))
                sys.stdout.flush()
                self.parseline(line)
                self.line_count += 1

        print "File parsed and loaded in memory"

        if self.output:
            self.swb.save(self.output)

    def parseline(self, line):
        if self.dumping_conf:
            if line.find("END CONFIG.PY DUMP") > 0:
                self.dumping_conf = False
                fo = open("config.py", "wb")
                for i in self.confpy:
                    fo.write(i)

                fo.close()
                return
            else:
                ln = line.split("mining")
                if len(ln) > 1:
                    self.confpy.append(ln[1])

        if self.rskmode:
            if line.find("RSKLOG") < 0:
                return
        else:
            if line.find("STRLOG") < 0:
                return

        if not self.complete:
            if line.find("SHARE_RECEIVED") < 0 and line.find("SUBMITBLOCK") < 0 and line.find("BLOCK_RECEIVED") < 0:
                return

        if line.find("MINER EMIT") > 0:
            return

        if self.notify and line.find("MINNOT") > 0:
            res = ast.literal_eval(line.split('#')[1].strip())
            event = res['tag']
        else:
            res = json.loads(line.split('#')[1].strip())
            event = res['tag']

        if self.notify:
            if event == "[MINNOT]":
                if self.curr_notify_id != "":
                    if res['data'] != self.curr_notify_id:
                        self.swb_notify.append([self.timestamp_to_str(self.notify_events[0]['start']), delta_ms(self.notify_events[0]['start'], self.notify_events[-1]['start'])])
                        self.notify_events = []
                        self.curr_notify_id = res['data']
                        self.notify_events.append(res)
                    else:
                        self.notify_events.append(res)
                else:
                    print "notify id blank, getting %s" % res['data']
                    self.curr_notify_id = res['data']
                    self.notify_events.append(res)

        if self.rskmode:
            if self.complete:
                if event == "[RSK_NEW_BLOCK_PARENT]":
                    self.swb_rnbp.append([res['uuid'], self.timestamp_to_str(res['start']), (float(res['elapsed'] * 1000))])
                elif event == "[RSK_NEW_WORK_UNIT]":
                    self.swb_rnwu.append([res['uuid'], self.timestamp_to_str(res['start']), (float(res['elapsed'] * 1000))])
            if event == "[RSK_BLOCK_RECEIVED_START]":
                if self.debug:
                    self.swb_rbrs.append([res['uuid'], res['start']])
                self.rsk_block_received_start.append(res)
            elif event == "[RSK_BLOCK_RECEIVED_TEMPLATE]":
                if self.debug:
                    self.swb_rbrt.append([res['uuid'], res['start'], res['data']])
                self.process_rsk_blockreceived_event(res)
            elif event == "[RSK_BLOCK_RECEIVED_END]":
                if self.debug:
                    self.swb_rbre.append([res['uuid'], res['start'], res['data']])
                self.rsk_block_received_end.append(res)
            elif event == "[RSK_SUBMITBLOCK]":
                if self.debug:
                    self.swb_rsb.append([res['uuid'], res['start'], res['data']])
                self.rsk_submitblock.append(res)

        if self.complete:
            if event == "[BTC_NEW_BLOCK_PARENT]":
                self.swb_bnbp.append([res['uuid'], self.timestamp_to_str(res['start']), (float(res['elapsed'] * 1000))])
            elif event == "[BTC_NEW_WORK_UNIT]":
                self.swb_bnwu.append([res['uuid'], self.timestamp_to_str(res['start']), (float(res['elapsed'] * 1000))])
            elif event == "[WORK_SENT]":
                self.swb_ws.append([res['uuid'], self.timestamp_to_str(res['start']), (float(res['elapsed'] * 1000))])
            elif event == "[WORK_SENT_OLD]":
                self.swb_wso.append([res['uuid'], self.timestamp_to_str(res['start']), (float(res['elapsed'] * 1000))])

        if event == "[BTC_BLOCK_RECEIVED_START]":
            if self.debug:
                self.swb_bbrs.append([res['uuid'], res['start']])
            self.btc_block_received_start.append(res)
        elif event == "[BTC_BLOCK_RECEIVED_TEMPLATE]":
            if self.debug:
                self.swb_bbrt.append([res['uuid'], res['start'], res['data']])
            self.process_btc_blockreceived_event(res)
        elif event == "[BTC_BLOCK_RECEIVED_END]":
            if self.debug:
                self.swb_bbre.append([res['uuid'], res['start'], res['data']])
            self.btc_block_received_end.append(res)
        elif event == "[SHARE_RECEIVED_START]":
            if self.debug:
                self.swb_srs.append([res['uuid'], res['start']])
            self.share_received_start.append(res)
        elif event == "[SHARE_RECEIVED_HEX]":
            if self.debug:
                self.swb_srh.append([res['uuid'], res['start'], res['data']])
            self.share_received_hex.append(res)
        elif event == "[BTC_SUBMITBLOCK]":
            if self.debug:
                self.swb_bsb.append([res['uuid'], res['start'], res['data']])
            self.btc_submitblock.append(res)
        elif event == "[SUBMITBLOCK_END]":
            if self.debug:
                self.swb_sb.append([res['uuid'], res['start'], res['data']])
            self.process_submitblock_event(res)
        elif event == "[PROCESS]":
            self.swb_process.append([self.timestamp_to_str(res['start']), res['data']['threads'][0]['cpu_percent'], res['data']['threads'][1]['cpu_percent'], res['data']['memory_percent']])


    def timestamp_to_str(self, tm):
        return datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S.%f')

    def process_rsk_blockreceived_event(self, ev):
        end_match = [x for x in self.rsk_block_received_end if x['data'] == ev['data']][0]
        sta_match = [x for x in self.rsk_block_received_start if x['uuid'] == ev['uuid']][0]
        dat = {"uuid" : sta_match['uuid'], "start" : self.timestamp_to_str(sta_match['start']), "delta_gbt" : delta_ms(sta_match['start'], end_match['start']), "delta_emit" : delta_ms(float(end_match['start'] + end_match['elapsed']), ev['start']), "clients" : end_match['clients']}
        if self.complete:
            self.swb_rbrev.append([dat['uuid'], dat['start'], dat['delta_gbt'], dat['clients'], dat['delta_emit']])
        self.sws.append(["getblocktemplate", dat['start'], dat['delta_gbt'], dat['uuid'], dat['clients'], dat['delta_emit'], "RSK"])
        self.rsk_block_received_end = [x for x in self.rsk_block_received_end if x['uuid'] != end_match['uuid']]
        self.rsk_block_received_start = [x for x in self.rsk_block_received_start if x['uuid'] != sta_match['uuid']]
        self.rsk_block_received_templ = [x for x in self.rsk_block_received_templ if x['uuid'] != ev['uuid']]

    def process_btc_blockreceived_event(self, ev):
        try:
            if self.rskmode:
                end_match = [x for x in self.btc_block_received_end if x['data'] == ev['data']][0]
                sta_match = [x for x in self.btc_block_received_start if x['uuid'] == ev['uuid']][0]
                dat = {"uuid" : sta_match['uuid'], "start" : self.timestamp_to_str(sta_match['start']), "delta_gbt" : delta_ms(sta_match['start'], end_match['start']), "delta_emit" : delta_ms(float(end_match['start'] + end_match['elapsed']), ev['start']), "clients" : end_match['clients']}
                if self.complete:
                    self.swb_bbrev.append([dat['uuid'], dat['start'], dat['delta_gbt'], dat['clients'], dat['delta_emit']])
                self.sws.append(["getblocktemplate", dat['start'], dat['delta_gbt'], dat['uuid'], dat['clients'], dat['delta_emit']])
                self.btc_block_received_end = [x for x in self.btc_block_received_end if x['uuid'] != end_match['uuid']]
                self.btc_block_received_start = [x for x in self.btc_block_received_start if x['uuid'] != sta_match['uuid']]
                self.btc_block_received_templ = [x for x in self.rsk_block_received_templ if x['uuid'] != ev['uuid']]
            else:
                end_match = [x for x in self.btc_block_received_end if x['data'] == ev['data'][0]][0]
                sta_match = [x for x in self.btc_block_received_start if x['uuid'] == ev['uuid']][0]
                dat = {"uuid" : sta_match['uuid'], "start" : self.timestamp_to_str(sta_match['start']), "delta_gbt" : delta_ms(sta_match['start'], end_match['start']), "delta_emit" : delta_ms(ev['start'], float(end_match['start'] + end_match['elapsed'])), "clients" : end_match['clients']}
                if self.complete:
                    self.swb_bbrev.append([dat['uuid'], dat['start'], dat['delta_gbt'], dat['clients'], dat['delta_emit']])
                self.sws.append(["getblocktemplate", dat['start'], dat['delta_gbt'], dat['uuid'], dat['clients'], dat['delta_emit']])
                self.btc_block_received_end = [x for x in self.btc_block_received_end if x['uuid'] != end_match['uuid']]
                self.btc_block_received_start = [x for x in self.btc_block_received_start if x['uuid'] != sta_match['uuid']]
                self.btc_block_received_templ = [x for x in self.rsk_block_received_templ if x['uuid'] != ev['uuid']]
        except IndexError as e:
            #print e
            pass

    def sb_match_helper(self, match, ev):
        n_ev = {"start" : "", "delta_process" : "", "delta_emit" : "", "hex" : ""}
        shhex_match = [x for x in self.share_received_hex if x['data'] == ev['data']][0]
        shstr_match = [x for x in self.share_received_start if x['uuid'] == shhex_match['uuid']][0]
        n_ev["start"] = self.timestamp_to_str(shstr_match["start"])
        if self.rskmode:
            n_ev["delta_process"] = delta_ms(shstr_match["start"], match["elapsed"])
        else:
            n_ev["delta_process"] = delta_ms(shstr_match["start"], match["start"])
        if self.rskmode:
            n_ev["delta_emit"] = delta_ms(match["elapsed"], (float(ev["start"]) + float(ev["elapsed"])))
        else:
            n_ev["delta_emit"] = delta_ms(match["start"], (float(ev["start"]) + float(ev["elapsed"])))
        n_ev["hex"] = ev["data"]
        if self.rskmode:
            if 'BTC' in match['tag']:
                self.share_received_hex = [x for x in self.share_received_hex if x['data'] != shhex_match['data']]
                self.share_received_start = [x for x in self.share_received_start if x['uuid'] != shstr_match['uuid']]
        else:
            self.share_received_hex = [x for x in self.share_received_hex if x['data'] != shhex_match['data']]
            self.share_received_start = [x for x in self.share_received_start if x['uuid'] != shstr_match['uuid']]
            self.share_received_hex = [x for x in self.share_received_hex if x['start'] < (ev['start'] - 60)]
            self.share_received_start = [x for x in self.share_received_start if x['start'] < (ev['start'] - 60)]

        return n_ev

    def process_submitblock_event(self, ev):
        if self.rskmode and self.complete:
            rsksb_match = [x for x in self.rsk_submitblock if x['data'] == ev['data']]
            if len(rsksb_match) > 0:
                rdat = self.sb_match_helper(rsksb_match[0], ev)
                self.sws.append(["submitblock", rdat['start'], rdat['delta_process'], rdat['hex'], 1, rdat['delta_emit'], "RSK"])
                self.rsk_submitblock = [x for x in self.rsk_submitblock if x['data'] != ev['data']]
        btcsb_match = [x for x in self.btc_submitblock if x['data'] == ev['data']]
        if len(btcsb_match) > 0:
            dat = self.sb_match_helper(btcsb_match[0], ev)
            self.sws.append(["submitblock", dat['start'], dat['delta_process'], dat['hex'], 1, dat['delta_emit']])
            self.btc_submitblock = [x for x in self.btc_submitblock if x['data'] != ev['data']]

def main():
    logfile = RSKParser(args.logFile, args.output, args.rskmode, args.complete, args.debug, args.notify)
    logfile.parse()

if __name__ == "__main__":
    main()
