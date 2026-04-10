ps <- get_pumpstations() %>%
  filter(str_detect(CMMS_ASSET_ID, "^LS-|^BPS"))

gv <- get_sewer_pipes() %>%
  filter(SUBTYPE=="1")

mh <- get_manholes()





gv %>%
  st_drop_geometry() %>%
  rowwise() %>%
  filter(AVAIL_NUM =="2022-0458") %>%
  write_csv("out/g.csv")

mh %>%
  st_drop_geometry() %>%
  rowwise() %>%
  filter(AVAIL_NUM =="2022-0458") %>%
  mutate(btm=RIM_ELEVATION-DEPTH) %>%
  write_csv("out/m.csv")

  mutate(z=mn-btm) %>%
  mutate(V_gal=5.875*MANHOLE_SIZE^2*z) %>%
  summarize(V_gal=sum(V_gal, na.rm=TRUE), n_mh=n()) %>%
  arrange(desc(AVAIL_NUM))


full_join(
gv %>%
  st_drop_geometry() %>%
  rowwise() %>%
  mutate(PIPE_SIZE=ifelse(PIPE_SIZE<8,8,PIPE_SIZE)) %>%
  mutate(MEASURED_LENGTH=ifelse(MEASURED_LENGTH<0,0,MEASURED_LENGTH)) %>%
  #filter(AVAIL_NUM =="2020-2973") %>%
  group_by(RECEIVING_STATION) %>%
  mutate(V_gal=5.875*(PIPE_SIZE/12)^2*MEASURED_LENGTH) %>%
  summarize(V_gal=sum(V_gal, na.rm=TRUE), L_ft=sum(MEASURED_LENGTH, na.rm=TRUE))
,
mh %>%
  st_drop_geometry() %>%
  rowwise() %>%
  #filter(AVAIL_NUM =="2020-2973") %>%
  mutate(RECEIVING_STATION=RECEIVING_PUMPSTATION) %>%
  mutate(MANHOLE_SIZE=ifelse(MANHOLE_SIZE<4, 4, MANHOLE_SIZE)) %>%

  group_by(RECEIVING_STATION) %>%
  mutate(mn=min(RIM_ELEVATION)) %>%
  mutate(btm=RIM_ELEVATION-DEPTH) %>%
  mutate(z=mn-btm) %>%
  mutate(z=ifelse(z<0, 0, z)) %>%
  mutate(V_gal=5.875*MANHOLE_SIZE^2*z) %>%
  summarize(V_gal=sum(V_gal, na.rm=TRUE), n_mh=n())
,
by="RECEIVING_STATION") %>%
  rowwise() %>%
  mutate(V_gal.x=ifelse(V_gal.x<=0, NA, V_gal.x)) %>%
  mutate(V_gal.y=ifelse(V_gal.y<=0, NA, V_gal.y)) %>%
  mutate(V_gal=sum(c(V_gal.x,V_gal.y), na.rm=TRUE)) %>%
  mutate(V_gal=ifelse(is.na(V_gal.x)&!is.na(V_gal.y), V_gal.y*2, V_gal)) %>%
  mutate(V_gal=ifelse(is.na(V_gal.y)&!is.na(V_gal.x), V_gal.x*2, V_gal)) %>%
  filter(!is.na(V_gal)) %>%
  mutate(V_gal.x=ifelse(is.na(V_gal.x), V_gal-V_gal.y, V_gal.x)) %>%
  mutate(V_gal.y=ifelse(is.na(V_gal.y), V_gal-V_gal.x, V_gal.y)) -> storage

ps <- read_csv("data/PumpStationFlows2025.csv")

storage %>%
  filter(!str_detect(RECEIVING_STATION, ",")) %>%
  filter(V_gal>0) %>%
  filter(str_detect(RECEIVING_STATION, "^LS-")) %>%
  dplyr::select(RECEIVING_STATION, V_gal) %>%
  left_join(ps, by=c("RECEIVING_STATION"="Asset ID")) %>%
  mutate(hold_time_avg_hrs=V_gal/`JEA Actual ADF\n(GPD)`*24) %>%
  mutate(hold_time_peak_hrs=V_gal/`JEA Design PHF\n(GPM)`/60) %>%
  write.csv("out/hold_time_test.csv")





load("f:/temp/ls_cost.RData")

raw %>%
  left_join(storage, by=c("AvailNumber"="AVAIL_NUM")) %>% #glimpse()
  dplyr::select(1, 3:4, 16:18,`PHF (GPM)`,V_gal, L_ft, n_mh) %>% #glimpse()
  rowwise() %>%
  mutate(hold_time_hr=V_gal/`PHF (GPM)`/60) %>%
  mutate(hold_time_hr=min(hold_time_hr, 12)) -> df

#df %>% write.csv("out/hold_time.csv")

df %>% count(is.na(hold_time_hr))

df %>%
  filter(hold_time_hr < 9) %>%
  ggplot(aes(`PHF (GPM)`, hold_time_hr)) +
  geom_point() +
  geom_hline(yintercept=2) +
  labs(x="Peak Hour Flow (GPM)")

df %>%
  distinct() -> df

df %>%
  filter(hold_time_hr < 9) %>%
  ggplot(aes(`PHF (GPM)`, hold_time_hr)) +
  geom_point() +
  geom_hline(yintercept=2, lty=2) +
  geom_vline(xintercept=100, lty=2) +
  labs(x="Peak Hour Flow (GPM)", y="Peak Hold Time (Hours)") +
  geom_label_repel(
     aes(label=AvailNumber)
    , data=df %>% filter(str_detect(AvailNumber,'2022-0458|2021-4413|2021-3699|2018-1473|2019-0386|2021-6105|2018-0119|2019-1266|2020-2433|2020-0720|2021-2231|2020-0195'))
    , max.overlaps=Inf
    , box.padding = 1
    ) +
  geom_point(
    , data=df %>% filter(str_detect(AvailNumber,'2022-0458|2021-4413|2021-3699|2018-1473|2019-0386|2021-6105|2018-0119|2019-1266|2020-2433|2020-0720|2021-2231|2020-0195'))
    , color="red"
  )

df %>%
  filter(hold_time_hr < 5) %>%
  filter(`PHF (GPM)` > 150) %>% View()

df %>%
  filter(AvailNumber=='2020-0720'|AvailNumber=='2021-2231'|AvailNumber=='2020-0195')



df %>%
  filter(hold_time_hr < 9) %>%
  ggplot(aes(L_ft, hold_time_hr)) +
  geom_point() +
  geom_hline(yintercept=2)



df %>%
  filter(hold_time_hr < 9) %>%
  filter(n_mh<100) %>%
  ggplot(aes(n_mh, hold_time_hr)) +
  geom_point() +
  geom_hline(yintercept=2, lty=2) +
  labs(x="Number of Manholes", y="Peak Hour Hold Time (Hours)")

df %>%
  filter(hold_time_hr < 9) %>%
  filter(n_mh<100) %>%
  ggplot(aes(n_mh, `PHF (GPM)`)) +
  geom_point() +
  labs(x="Number of Manholes", y="Peak Hour Flow (GPM)") +
  geom_smooth(method="lm", se=FALSE)

df %>%
  ggplot(aes(hold_time_hr)) +
  stat_ecdf() +
  geom_vline(xintercept=2) +
  geom_hline(yintercept=.16) +
  labs(x="Peak Hour Hold Time (hours)", y="Cumulative Percentage of Stations")


  geom_histogram(fill=JEA.Dark) +
  geom_vline(xintercept=2)

