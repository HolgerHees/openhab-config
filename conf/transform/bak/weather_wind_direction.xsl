<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0">       
   <xsl:output indent="yes" method="xml" encoding="UTF-8" omit-xml-declaration="yes" />
   <xsl:template match="/">
      <!-- format: hh:mm:ss -->
      <xsl:value-of select="//response/current_observation/wind_dir/text()" />
   </xsl:template>
</xsl:stylesheet>
