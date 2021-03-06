from django.db import models
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg, Count, Min, Sum
from django.db.models.signals import m2m_changed
from django.db.models import Q, UniqueConstraint

# def bids_changed(sender, **kwargs):
#     bid_num = kwargs['instance'].bid.count()
#     bid_allowed_num = kwargs['instance'].tender.bidder_num
#     if bid_num > bid_allowed_num :
#         raise ValidationError("竞标数%s家超过标的允许的%s家" % (bid_num, bid_allowed_num))
#
# m2m_changed.connect(bids_changed, sender=Record.bid.through)

REGION_CHOICES = [
    ('北京', '北京'),
    ('天津', '天津'),
    ('上海', '上海'),
    ('重庆', '重庆'),
    ('广州', '广州'),
    ('深圳', '深圳'),
    ('成都', '成都'),
    ('沈阳', '沈阳'),
    ('大连', '大连'),
    ('西安', '西安'),
    ('厦门', '厦门'),
    ('河北', '河北'),
    ('山西', '山西'),
    ('内蒙古', '内蒙古'),
    ('辽宁', '辽宁'),
    ('吉林', '吉林'),
    ('黑龙江', '黑龙江'),
    ('江苏', '江苏'),
    ('浙江', '浙江'),
    ('安徽', '安徽'),
    ('福建', '福建'),
    ('江西', '江西'),
    ('山东', '山东'),
    ('河南', '河南'),
    ('湖北', '湖北'),
    ('湖南', '湖南'),
    ('广东', '广东'),
    ('广西', '广西'),
    ('海南', '海南'),
    ('四川', '四川'),
    ('贵州', '贵州'),
    ('云南', '云南'),
    ('西藏', '西藏'),
    ('陕西', '陕西'),
    ('甘肃', '甘肃'),
    ('青海', '青海'),
    ('宁夏', '宁夏'),
    ('新疆（含兵团）', '新疆（含兵团）'),
]


D_MAIN_SPEC = {
    '阿卡波糖口服常释剂型': {
        '50mg': 1,
        '100mg': 2,
    },
    '阿莫西林口服常释剂型': {
        '0.25g': 1,
        '0.5g': 2,
    },
    '阿奇霉素口服常释剂型': {
        '0.25g': 1,
        '0.5g': 2,
    },
    '安立生坦片': {
        '5mg': 1,
        '10mg': 2,
    },
    '奥美沙坦酯口服常释剂型': {
        '20mg': 1,
        '40mg': 2,
    },
    '比索洛尔口服常释剂型': {
        '2.5mg': 0.5,
        '5mg': 1,
    },
    '多奈哌齐口服常释剂型': {
        '5mg': 1,
        '10mg': 2
    },
    '氟康唑口服常释剂型': {
        '50mg': 1,
        '150mg': 3
    },
    '格列美脲口服常释剂型': {
        '1mg': 0.5,
        '2mg': 1,
    },
    '坎地沙坦酯口服常释剂型': {
        '4mg': 0.5,
        '8mg': 1
    },
    '克林霉素口服常释剂型': {
        '0.075g': 0.5,
        '0.15g': 1
    },
    '索利那新口服常释剂型': {
        '5mg': 1,
        '10mg': 2
    },
    '特拉唑嗪口服常释剂型': {
        '1mg': 0.5,
        '2mg': 1
    },
    '替吉奥口服常释剂型': {
        '20mg': 1,
        '25mg': 1.2
    },
    '头孢氨苄口服常释剂型': {
        '0.25g': 1,
        '0.5g': 2
    },
    '辛伐他汀口服常释剂型': {
        '20mg': 1,
        '40mg': 2
    },
    '异烟肼口服常释剂型': {
        '0.1g': 1,
        '0.3g': 3
    }
}


class Tender(models.Model):
    target = models.CharField(max_length=30, verbose_name='带量品种')
    vol = models.CharField(max_length=30, verbose_name='批次')
    tender_begin = models.DateField(verbose_name='标期起始日期')
    bidder_num = models.IntegerField(verbose_name='竞标者数量')

    class Meta:
        verbose_name = '集采标的'
        verbose_name_plural = '集采标的'
        ordering = ['target']
        unique_together = ['target', 'vol']

    def __str__(self):
        return "%s %s %s家竞标" % (self.vol, self.target, self.bidder_num)

    @property
    def proc_percentage(self):
        if self.bidder_num == 1:  # 1家竞标，带量采购合同里量占报量的50%，下同
            return 0.5
        elif 2 <= self.bidder_num <= 3:
            return 0.6
        elif self.bidder_num == 4:
            return 0.7
        elif self.bidder_num > 4:
            return 0.8
        else:
            return None

    def get_specs(self):  # 所有相关报量里出现的规格
        return self.volume_set.all().order_by('spec').values_list('spec', flat=True).distinct()

    @property
    def main_spec(self):  # 区分主规格，字典里折算index为1的是主规格
        try:
            for spec in self.get_specs():
                if D_MAIN_SPEC[self.target][spec] == 1:
                    return spec
        except:
            return self.get_specs()[0]

    @property
    def specs_num(self):  # 规格数量
        return len(self.get_specs())

    def total_std_volume_contract(self):  # 计算报量总和
        if self.specs_num == 1:
            qs = self.volume_set.all()
            if qs.exists():
                return qs.aggregate(Sum('amount_contract'))['amount_contract__sum']
            else:
                return 0
        else :  # 如果不止一种规格要折算后再求和
            volume = 0
            for spec in self.get_specs():
                qs = self.volume_set.all().filter(spec=spec)
                if qs.exists():
                    volume += qs.aggregate(Sum('amount_contract'))['amount_contract__sum'] * \
                              D_MAIN_SPEC[self.target][spec]
                else:
                    volume += 0
            return volume

    @property
    def tender_period(self):
        if self.bidder_num == 1:  # 1家竞标，标期1年
            return 1
        elif 2 <= self.bidder_num <= 4:
            return 2
        elif self.bidder_num > 4:
            return 3

    @property
    def tender_end(self):
        year = timedelta(days=365)  # 1年
        return self.tender_begin + self.tender_period * year

    @property
    def winner_num_max(self):
        if self.bidder_num == 1:  # 1家竞标，1家中标，下同
            return 1
        elif 2 <= self.bidder_num <= 3:
            return 2
        elif self.bidder_num == 4:
            return 3
        elif 5 <= self.bidder_num <= 6:
            return 4
        elif 7 <= self.bidder_num <= 8:
            return 5
        elif self.bidder_num > 8:
            return 6

    @property
    def regions(self):
        return self.volume_set.all().order_by('region').values_list('region', flat=True).distinct()

    def winners(self):
        winner_ids = [bid.id for bid in self.bid_set.all() if bid.is_winner()]
        return self.bid_set.filter(id__in=winner_ids).order_by('bid_price')


class Company(models.Model):
    name = models.CharField(max_length=50, verbose_name='企业名称', unique=True)
    mnc_or_local =  models.BooleanField(verbose_name='是否跨国企业')

    class Meta:
        verbose_name = '制药企业'
        verbose_name_plural = '制药企业'
        ordering = ['name']

    def __str__(self):
        return self.name


class Bid(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, verbose_name='所属记录')
    bidder = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='竞标厂商')
    origin = models.BooleanField(verbose_name='是否该标的原研')
    bid_price = models.FloatField(verbose_name='报价')
    original_price = models.FloatField(verbose_name='集采前最低价', blank=True, null=True)

    class Meta:
        verbose_name = '投标记录'
        verbose_name_plural = '投标记录'
        ordering = ['-bid_price']
        unique_together = (('tender', 'bidder'),)

    def __str__(self):
        return "%s %s %s" % (self.tender.__str__(), self.bidder, self.bid_price)

    def is_winner(self):  # 该bid是否中标
        qs = self.volume_set.all()
        if qs.exists():
            return True
        else:
            return False

    def price_cut(self):  # 相比集采前降价幅度
        try:
            return self.bid_price/self.original_price -1
        except:
            return None

    def regions_win(self):
        return self.volume_set.all().order_by('region').values_list('region', flat=True).distinct()

    def std_volume_win(self, spec=None, region=None):
        volume = 0
        if spec is not None and region is not None:
            qs = self.volume_set.filter(spec=spec, region=region)
            if qs.exists():
                volume = qs[0].amount_contract
            else:
                volume = 0
        elif spec is not None and region is None:
            qs = self.volume_set.filter(spec=spec)
            if qs.exists():
                volume = qs.aggregate(Sum('amount_contract'))['amount_contract__sum']
            else:
                volume = 0
        elif spec is None and region is not None:
            if self.tender.specs_num == 1:
                qs = self.volume_set.filter(region=region)
                if qs.exists():
                    volume = qs.aggregate(Sum('amount_contract'))['amount_contract__sum']
                else:
                    volum = 0
            else:
                volume = 0
                for spec in self.tender.get_specs():
                    qs = self.volume_set.filter(spec=spec, region=region)
                    if qs.exists():
                        volume += qs.aggregate(Sum('amount_contract'))['amount_contract__sum'] * D_MAIN_SPEC[self.tender.target][spec]
                    else:
                        volume += 0
        else:
            if self.tender.specs_num == 1:
                qs = volume = self.volume_set.all()
                if qs.exists():
                    volume = qs.aggregate(Sum('amount_contract'))['amount_contract__sum']
                else:
                    volume = 0
            else:
                volume = 0
                for spec in self.tender.get_specs():
                    qs = self.volume_set.all().filter(spec=spec)
                    if qs.exists():
                        volume += qs.aggregate(Sum('amount_contract'))['amount_contract__sum'] * \
                                  D_MAIN_SPEC[self.tender.target][spec]
                    else:
                        volume += 0
        return volume

    def value_win(self):
        return self.std_volume_win() * self.bid_price

    def clean(self):
        try:
            bid_num = self.tender.bid_set.exclude(pk=self.pk).count()
            bid_allowed_num = self.tender.bidder_num
            if bid_num >= bid_allowed_num:
                raise ValidationError('同一记录下竞标数量%s家已达到标的允许的%s家' % (bid_num, bid_allowed_num))
        except ObjectDoesNotExist:
            pass

        try:
            if self.tender.bid_set.filter(origin=True).exclude(pk=self.pk).count() > 0 and self.origin is True:  # 只能有1家原研
                raise ValidationError('同一记录下最多只能有1家原研')
        except ObjectDoesNotExist:
            pass


class Volume(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, verbose_name='标的')
    region = models.CharField(max_length=10, choices=REGION_CHOICES, verbose_name='区域')
    spec = models.CharField(max_length=10, verbose_name='规格')
    amount_contract = models.FloatField(verbose_name='合同量')
    winner = models.ForeignKey(Bid, on_delete=models.CASCADE, verbose_name='中标供应商', blank=True, null=True)

    class Meta:
        verbose_name = '地方报量'
        verbose_name_plural = '地方报量'
        ordering = ['tender', 'region', 'spec']

    def __str__(self):
        return "%s %s %s %s" % (self.tender.target, self.region, self.spec, self.amount_contract)