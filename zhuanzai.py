import requests
import json
import logging

def fetch_jisilu_cb_list():
    url = "https://www.jisilu.cn/webapi/cb/list/"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cookie": "Hm_lvt_164fe01b1433a19b507595a43bf58262=1741170762; kbzw__Session=479a6bvnufhrq0pbohnie91hc6",
        "if-modified-since": "Thu, 24 Apr 2025 09:20:56 GMT",
        "referer": "https://www.jisilu.cn/web/data/cb/list",
        "sec-ch-ua": '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        "columns": "1,70,2,3,5,6,11,12,14,15,16,29,30,32,34,44,46,47,50,52,53,54,56,57,58,59,60,62,63,67",
        "init": "1",
        "priority": "u=1, i",
        "cookie": "kbzw__Session=479a6bvnufhrq0pbohnie91hc6; Hm_lvt_164fe01b1433a19b507595a43bf58262=1745486622; HMACCOUNT=255FF234E45225DB; kbz_newcookie=1; kbzw__user_login=7Obd08_P1ebax9aXwZOpkrCnq6qUpIKvpuXK7N_u0ejF1dSerZSgxNmvrc2uoNuaqsTY29SwktLCq62roaqerMWvlqiYrqXW2cXS1qCbqp2qlKyUmLKgubXOvp-qrJ2uoK-YrJasmK6ltrG_0aTC2PPV487XkKylo5iJx8ri3eTg7IzFtpaSp6Wjs4HHyuKvqaSZ5K2Wn4G45-PkxsfG1sTe3aihqpmklK2Xm8OpxK7ApZXV4tfcgr3G2uLioYGzyebo4s6onaqXpJGlp6GogcPC2trn0qihqpmklK2XuNzIn5KnrqOZp5ylkg..; Hm_lpvt_164fe01b1433a19b507595a43bf58262=1745486666"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # 统计部分
    items = data.get('data', [])
    total_bonds = len(items)
    print(f"转债总数: {total_bonds}")

    # 涨跌统计
    up_count = 0
    down_count = 0
    zero_count = 0
    up_bins = [0, 0, 0, 0]   # 0-1, 1-2, 2-3, 3+
    down_bins = [0, 0, 0, 0] # 0-1, 1-2, 2-3, 3+

    for item in items:
        rt = item.get('increase_rt')
        if rt is None:
            continue
        if rt > 0:
            up_count += 1
            if 0 < rt <= 1:
                up_bins[0] += 1
            elif 1 < rt <= 2:
                up_bins[1] += 1
            elif 2 < rt <= 3:
                up_bins[2] += 1
            elif rt > 3:
                up_bins[3] += 1
        elif rt < 0:
            down_count += 1
            abs_rt = abs(rt)
            if 0 < abs_rt <= 1:
                down_bins[0] += 1
            elif 1 < abs_rt <= 2:
                down_bins[1] += 1
            elif 2 < abs_rt <= 3:
                down_bins[2] += 1
            elif abs_rt > 3:
                down_bins[3] += 1
        else:
            zero_count += 1

    result = []
    logger = logging.getLogger("cb_logger")

    # 统计输出
    result.append("==== 可转债涨跌幅统计 =====")
    result.append(f"总共可转债数量: {total_bonds}\n")
    result.append(f"上涨数量: {up_count} 个")
    result.append(f"下跌数量: {down_count} 个")
    result.append(f"涨跌幅为0的数量: {zero_count} 个\n")
    result.append("【上涨区间分布】")
    result.append(f"  0% < 涨幅 ≤ 1%   : {up_bins[0]:>3} 个")
    result.append(f"  1% < 涨幅 ≤ 2%   : {up_bins[1]:>3} 个")
    result.append(f"  2% < 涨幅 ≤ 3%   : {up_bins[2]:>3} 个")
    result.append(f"      涨幅 > 3%     : {up_bins[3]:>3} 个\n")
    result.append("【下跌区间分布】")
    result.append(f"  0% < 跌幅 ≤ 1%   : {down_bins[0]:>3} 个")
    result.append(f"  1% < 跌幅 ≤ 2%   : {down_bins[1]:>3} 个")
    result.append(f"  2% < 跌幅 ≤ 3%   : {down_bins[2]:>3} 个")
    result.append(f"      跌幅 > 3%     : {down_bins[3]:>3} 个")
    result.append("====================================")

    for line in result:
        logger.info(line)

    # 文字输出重点转债信息
    result.append("重点转债信息（前5只）：\n")
    for idx, item in enumerate(items[:5], 1):
        bond_id = item.get('bond_id', '')
        bond_nm = item.get('bond_nm', '')
        price = item.get('price', '')
        increase_rt = item.get('increase_rt', '')
        stock_nm = item.get('stock_nm', '')
        sprice = item.get('sprice', '')
        premium_rt = item.get('premium_rt', '')
        rating_cd = item.get('rating_cd', '')
        ytm_rt = item.get('ytm_rt', '')
        year_left = item.get('year_left', '')
        volume = item.get('volume', '')
        curr_iss_amt = item.get('curr_iss_amt', '')

        # 格式化
        increase_rt_str = f"{increase_rt:.2f}%" if isinstance(increase_rt, (int, float)) else str(increase_rt)
        premium_rt_str = f"{premium_rt:.2f}%" if isinstance(premium_rt, (int, float)) else str(premium_rt)
        ytm_rt_str = f"{ytm_rt:.2f}%" if isinstance(ytm_rt, (int, float)) else str(ytm_rt)
        year_left_str = f"{year_left:.2f}" if isinstance(year_left, (int, float)) else str(year_left)
        price_str = f"{price:.2f}" if isinstance(price, (int, float)) else str(price)
        sprice_str = f"{sprice:.2f}" if isinstance(sprice, (int, float)) else str(sprice)
        volume_str = f"{volume:.2f}" if isinstance(volume, (int, float)) else str(volume)
        curr_iss_amt_str = f"{curr_iss_amt:.2f}" if isinstance(curr_iss_amt, (int, float)) else str(curr_iss_amt)

        line = (f"{bond_nm} 现价:{price_str} 涨跌幅:{increase_rt_str} 正股:{stock_nm}({sprice_str}) "
                f"溢价率:{premium_rt_str} 评级:{rating_cd} 到期收益:{ytm_rt_str} "
                f"剩余年限:{year_left_str}年 成交额:{volume_str}万 剩余规模:{curr_iss_amt_str}亿")
        logger.info(line)
        result.append(line)
    # result.append("\n（仅展示前5只转债，更多请筛选查看）\n")
    # logger.info("（仅展示前5只转债，更多请筛选查看）")
    return "\n".join(result)

