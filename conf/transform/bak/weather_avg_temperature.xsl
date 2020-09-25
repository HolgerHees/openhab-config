<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0">       
   <xsl:output indent="yes" method="xml" encoding="UTF-8" omit-xml-declaration="yes" />
   <xsl:template match="/">
      <xsl:value-of select="sum(//response/hourly_forecast/forecast[position()&gt;4 and position()&lt;12]/temp/metric/text()) div count(//response/hourly_forecast/forecast[position()&gt;4 and position()&lt;12]/temp/metric/text())" />
   </xsl:template>
</xsl:stylesheet>
