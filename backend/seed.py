import sqlite3
import json
import os
import random
from datetime import datetime, timedelta
from db import get_conn, init_db, DB_PATH

random.seed(42)
TODAY      = datetime.now().date()
START_DATE = TODAY - timedelta(days=90)
JSON_PATH  = os.path.join(os.path.dirname(__file__), "../data/merchants.json")

SEGMENTS = ["restaurant","dark_kitchen","restaurant","dark_kitchen","restaurant"]
CITIES_MX = ["Ciudad de Mexico","Guadalajara","Monterrey","Puebla","Tijuana","Leon"]
CITIES_CO = ["Bogota","Medellin","Cali","Barranquilla"]
CITIES_CL = ["Santiago","Valparaiso","Concepcion"]
CITIES_BR = ["Sao Paulo","Rio de Janeiro","Curitiba"]
CITIES_PE = ["Lima","Arequipa"]
COUNTRIES = [("MX",CITIES_MX,0.5),("CO",CITIES_CO,0.2),("CL",CITIES_CL,0.15),("BR",CITIES_BR,0.1),("PE",CITIES_PE,0.05)]

RNAMES = ["Taqueria El Patron","La Cocina de Maria","Burger Lab","Sushi Express","Pizzeria Bella Roma","Cevicheria Lima","Arepas Don Pedro","El Asador","La Fondita","Tacos y Mas","Comida Casera","El Rincon Mexicano","La Parrilla","Mariscos El Puerto","Antojitos Mexicanos","Cocina Fusion","El Fogon","La Terraza","Sabores del Mar","Casa de Comidas","El Carnivoro","Mezze Mediterranean","Wok Express","La Empanada","Burritos Co","El Trompo","Pozoleria Don Chucho","Tostadas Coyoacan","Gorditas El Gordo","Chilaquiles y Mas","Tacos de Canasta","El Fogoncito","La Loncheria","Enchiladas El Rey","Tortas El Grande","Birrieria Don Ramon"]
DNAMES = ["Dark Kitchen CDMX","Ghost Kitchen Monterrey","Cloud Kitchen Bogota","Virtual Eats","Kitchen Hub","Multi-Brand Kitchen","Express Dark Kitchen","Ghost Burger Lab","Virtual Sushi","Cloud Tacos","Digital Kitchen","Smart Kitchen","Flavor Factory","The Kitchen Network","Rapid Eats Hub","Ghost Kitchen Santiago","Cloud Eats Lima","Virtual Kitchen CO","Dark Eats BR","Ghost Food Lab"]

def pick_cc():
    r = random.random(); c = 0
    for country,cities,prob in COUNTRIES:
        c += prob
        if r <= c: return country, random.choice(cities)
    return "MX", random.choice(CITIES_MX)

def mname(segment, used):
    pool = DNAMES if segment=="dark_kitchen" else RNAMES
    avail = [n for n in pool if n not in used]
    name = random.choice(avail) if avail else f"{random.choice(pool)} {random.randint(2,9)}"
    used.add(name); return name

def reset_db():
    if os.path.exists(DB_PATH): os.remove(DB_PATH); print("Old db removed.")
    init_db()

def seed_partner(conn, data):
    conn.execute("INSERT OR REPLACE INTO partners (partner_id,partner_name,rev_share_rate,contact_name,contact_whatsapp,contact_email) VALUES (?,?,?,?,?,?)",
        (data["partner_id"],data["partner_name"],data["rev_share_rate"],"Ana Rodrigues","+5511999990001","ana.rodrigues@ubereats.com"))
    print(f"Partner seeded: {data['partner_name']}")

def seed_original(conn, merchants, pid):
    for m in merchants:
        months = m.get("months_on_platform",12)
        jd = (TODAY - timedelta(days=months*30)).isoformat()
        conn.execute("INSERT OR REPLACE INTO merchants (merchant_id,partner_id,merchant_name,segment,country,city,business_type,platform_join_date,active_listings,customer_rating,avg_order_size,refund_rate,zero_sales_days_last_90d,avg_monthly_txn_count,gross_sales_trend,peak_season_months) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (m["merchant_id"],pid,m["merchant_name"],m["segment"],m["country"],m["city"],m["business_type"],jd,m.get("active_listings",20),m.get("customer_rating",4.5),m.get("avg_order_size",35),m.get("refund_rate",0.02),m.get("zero_sales_days_last_90d",3),m.get("avg_monthly_txn_count",280),m.get("gross_sales_trend",0.06),json.dumps(m.get("peak_season_months",[]))))
        fid = f"FIN-{m['merchant_id']}"
        pre = m.get("gross_sales_pre_avg_monthly",8000)
        conn.execute("INSERT OR REPLACE INTO financings (financing_id,merchant_id,partner_id,loan_amount,total_repayment_amount,repayment_rate,fixed_fee,status,disbursement_date,expected_days,days_since_disbursement,amount_repaid,is_first_credit,total_prior_credits,partner_revenue_share,gross_sales_pre_30d,gross_sales_pre_90d,gross_sales_pre_180d,gross_sales_pre_avg_monthly) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid,m["merchant_id"],pid,m["loan_amount"],m["total_repayment_amount"],0.14,m["loan_amount"]*0.17,m["financing_status"],m["disbursement_date"],m["expected_days"],m["days_since_disbursement"],m["amount_repaid"],1 if m["is_first_credit"] else 0,m["total_prior_credits"],m["partner_revenue_share"],pre*0.95,pre*2.9,pre*5.8,pre))
    print(f"{len(merchants)} original merchants seeded.")

def seed_synthetic(conn, pid, start_idx, count, months_range, weekly_target, top_mix=True):
    used = set(); ins = 0; rr = 0.025
    for i in range(count):
        mid = f"1001-S{start_idx+i:03d}"
        seg = random.choice(SEGMENTS); country,city = pick_cc()
        name = mname(seg,used); bt = "juridico" if seg=="dark_kitchen" else random.choice(["natural","juridico"])
        mop = random.randint(10,36); jd = (TODAY-timedelta(days=mop*30)).isoformat()
        pre = random.uniform(8000,25000); trend = random.uniform(0.03,0.12)
        conn.execute("INSERT OR IGNORE INTO merchants (merchant_id,partner_id,merchant_name,segment,country,city,business_type,platform_join_date,active_listings,customer_rating,avg_order_size,refund_rate,zero_sales_days_last_90d,avg_monthly_txn_count,gross_sales_trend,peak_season_months) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid,pid,name,seg,country,city,bt,jd,random.randint(15,40),round(random.uniform(4.2,5.0),1),round(random.uniform(25,65),2),round(random.uniform(0.01,0.04),3),random.randint(0,5),random.randint(180,500),round(trend,4),json.dumps([])))
        mo = random.randint(*months_range); ddate = TODAY-timedelta(days=mo*30)
        loan = round(random.uniform(5500,10000),2); fee = round(loan*0.17,2); total = round(loan+fee,2)
        exp_days = random.randint(60,120); ds = (TODAY-ddate).days
        rev = round(loan*rr,2)
        pace = random.uniform(1.1,1.5) if (top_mix and random.random()>0.4) else random.uniform(0.85,1.09)
        proj = total/exp_days; amr = min(round(proj*pace*ds,2),total)
        status = "PAID" if amr>=total else "ACTIVE"
        fid = f"FIN-{mid}"
        conn.execute("INSERT OR IGNORE INTO financings (financing_id,merchant_id,partner_id,loan_amount,total_repayment_amount,repayment_rate,fixed_fee,status,disbursement_date,expected_days,days_since_disbursement,amount_repaid,is_first_credit,total_prior_credits,partner_revenue_share,gross_sales_pre_30d,gross_sales_pre_90d,gross_sales_pre_180d,gross_sales_pre_avg_monthly) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid,mid,pid,loan,total,0.14,fee,status,ddate.isoformat(),exp_days,ds,amr,1,0,rev,round(pre*0.95,2),round(pre*2.9,2),round(pre*5.8,2),round(pre,2)))
        bd = pre/30
        uplift = random.uniform(1.4,1.85) if pace>=1.1 else random.uniform(1.05,1.35)
        tw = weekly_target/7
        all_days = [START_DATE+timedelta(days=j) for j in range(91)]
        post_days = [d for d in all_days if d>=ddate]
        zds = random.randint(0,5); zdset = set(random.sample(post_days,min(zds,len(post_days))))
        for day in all_days:
            if day>TODAY: continue
            is_post = day>=ddate
            if is_post and day in zdset: continue
            if is_post:
                dp = (day-ddate).days; prog = min(dp/exp_days,1.0)
                tgt = tw if (TODAY-day).days<=7 else bd*uplift*(0.7+0.3*prog)
                gs = max(0,round(tgt*random.uniform(0.85,1.18),2))
            else:
                gs = max(0,round(bd*random.uniform(0.78,1.22),2))
            rep = round(gs*0.14,2) if is_post else 0.0
            conn.execute("INSERT OR IGNORE INTO daily_sales (merchant_id,partner_id,financing_id,sale_date,gross_sales,repayment_amount,has_direct_gross_sales) VALUES (?,?,?,?,?,?,?)",
                (mid,pid,fid,day.isoformat(),gs,rep,1))
        ins += 1
    return ins

def seed_new_week(conn, pid, count):
    used = set(); ins = 0; rr = 0.025
    for i in range(count):
        mid = f"1001-N{i+1:03d}"
        seg = random.choice(SEGMENTS); country,city = pick_cc()
        name = mname(seg,used); bt = "juridico" if seg=="dark_kitchen" else random.choice(["natural","juridico"])
        mop = random.randint(8,24); jd = (TODAY-timedelta(days=mop*30)).isoformat()
        pre = random.uniform(7000,20000)
        conn.execute("INSERT OR IGNORE INTO merchants (merchant_id,partner_id,merchant_name,segment,country,city,business_type,platform_join_date,active_listings,customer_rating,avg_order_size,refund_rate,zero_sales_days_last_90d,avg_monthly_txn_count,gross_sales_trend,peak_season_months) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid,pid,name,seg,country,city,bt,jd,random.randint(14,35),round(random.uniform(4.3,5.0),1),round(random.uniform(22,60),2),round(random.uniform(0.01,0.04),3),random.randint(0,6),random.randint(150,420),round(random.uniform(0.04,0.10),4),json.dumps([])))
        doff = random.randint(0,4); ddate = TODAY-timedelta(days=doff)
        loan = round(random.uniform(6000,9500),2); fee = round(loan*0.17,2); total = round(loan+fee,2)
        exp_days = random.randint(75,110); ds = max((TODAY-ddate).days,1)
        rev = round(loan*rr,2); amr = round((total/exp_days)*ds*random.uniform(0.9,1.1),2)
        fid = f"FIN-{mid}"
        conn.execute("INSERT OR IGNORE INTO financings (financing_id,merchant_id,partner_id,loan_amount,total_repayment_amount,repayment_rate,fixed_fee,status,disbursement_date,expected_days,days_since_disbursement,amount_repaid,is_first_credit,total_prior_credits,partner_revenue_share,gross_sales_pre_30d,gross_sales_pre_90d,gross_sales_pre_180d,gross_sales_pre_avg_monthly) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid,mid,pid,loan,total,0.14,fee,"ACTIVE",ddate.isoformat(),exp_days,ds,amr,1,0,rev,round(pre*0.95,2),round(pre*2.9,2),round(pre*5.8,2),round(pre,2)))
        bd = pre/30*random.uniform(1.1,1.3)
        for j in range(ds+1):
            day = ddate+timedelta(days=j)
            if day>TODAY: continue
            gs = round(bd*random.uniform(0.88,1.15),2)
            rep = round(gs*0.14,2)
            conn.execute("INSERT OR IGNORE INTO daily_sales (merchant_id,partner_id,financing_id,sale_date,gross_sales,repayment_amount,has_direct_gross_sales) VALUES (?,?,?,?,?,?,?)",
                (mid,pid,fid,day.isoformat(),gs,rep,1))
        ins += 1
    return ins

def seed_applications(conn, pid, total_merchants):
    denied = random.randint(20,35)
    reasons = ["insufficient_sales_history","high_refund_rate","irregular_sales_pattern","kyc_incomplete"]
    for i in range(total_merchants):
        days_ago = random.randint(0,89)
        conn.execute("INSERT INTO credit_applications (partner_id,merchant_id,applied_at,status) VALUES (?,?,?,'APPROVED')",
            (pid,f"ph_{i}",(TODAY-timedelta(days=days_ago)).isoformat()))
    for i in range(denied):
        days_ago = random.randint(0,89)
        reason = random.choices(reasons,weights=[40,25,25,10])[0]
        conn.execute("INSERT INTO credit_applications (partner_id,merchant_id,applied_at,status,denial_reason) VALUES (?,?,?,'DENIED',?)",
            (pid,f"denied_{i}",(TODAY-timedelta(days=days_ago)).isoformat(),reason))
    print(f"{total_merchants+denied} credit applications seeded ({total_merchants} approved, {denied} denied).")

def main():
    print("\nSeeding Lucio database - 136 merchant portfolio...\n")
    with open(JSON_PATH) as f: data = json.load(f)
    orig = data["merchants"]; pid = data["partner_id"]
    reset_db(); conn = get_conn()
    try:
        seed_partner(conn, data)
        seed_original(conn, orig, pid)
        n1 = seed_synthetic(conn,pid,100,40,(2,4),15000,True)
        n2 = seed_synthetic(conn,pid,140,35,(4,6),13000,True)
        print(f"{n1+n2} synthetic merchants (loans 2-6 months ago) seeded.")
        n3 = seed_new_week(conn,pid,36)
        print(f"{n3} new merchants (disbursed this week) seeded.")
        seed_applications(conn,pid,len(orig)+n1+n2+n3)
        conn.commit()
        tm = conn.execute("SELECT COUNT(*) as n FROM merchants").fetchone()["n"]
        ts = conn.execute("SELECT COUNT(*) as n FROM daily_sales").fetchone()["n"]
        ws = conn.execute("SELECT COALESCE(SUM(gross_sales),0) as t FROM daily_sales WHERE sale_date >= date('now','-7 days')").fetchone()["t"]
        print(f"\nDatabase ready! Merchants: {tm} | Daily sales rows: {ts} | Weekly sales: ${ws:,.2f}\n")
    except Exception as e:
        conn.rollback(); print(f"Error: {e}"); raise
    finally: conn.close()

if __name__ == "__main__":
    main()
